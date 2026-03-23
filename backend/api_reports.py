"""
Report generation endpoints — POST /reports/generate

Supports XLSX and PDF export of:
  overview, asset_health, critical_assets, pm_suggestions, insights
"""

import io
import math
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from .auth import decode_token, get_user_locations
from .prediction_storage import (
    retrieve_failure_predictions,
    retrieve_pm_optimization_suggestions,
    retrieve_maintenance_insights,
)

router = APIRouter(prefix="/reports", tags=["Reports"])
bearer = HTTPBearer()

# ── Brand palette ──────────────────────────────────────────────────────────────
INDIGO      = "#6366f1"
INDIGO_DARK = "#4338ca"
INDIGO_LIGHT= "#818cf8"
EMERALD     = "#34d399"
SLATE_50    = "#f8fafc"
SLATE_100   = "#f1f5f9"
SLATE_200   = "#e2e8f0"
SLATE_700   = "#334155"
SLATE_900   = "#0f172a"
WHITE       = "#ffffff"
RISK_COLORS = {
    "CRITICAL": "#ef4444",
    "HIGH":     "#f97316",
    "MEDIUM":   "#f59e0b",
    "LOW":      "#10b981",
}
RISK_BG = {
    "CRITICAL": "#fef2f2",
    "HIGH":     "#fff7ed",
    "MEDIUM":   "#fffbeb",
    "LOW":      "#f0fdf4",
}
IMPACT_COLORS = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}


def _current_location(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    user_id = int(payload["sub"])
    locs = get_user_locations(user_id)
    if not locs:
        raise HTTPException(400, "No locations found for this user")
    return locs[0]["id"]


def _get_org_name(location_id: int) -> str:
    """Return the org name for a location, slugified for use in filenames."""
    from .auth import _get_conn
    import re
    conn = _get_conn()
    row = conn.execute(
        "SELECT o.name FROM orgs o JOIN locations l ON l.org_id = o.id WHERE l.id = ?",
        (location_id,)
    ).fetchone()
    conn.close()
    name = row["name"] if row else "org"
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


class ReportRequest(BaseModel):
    sections: List[str]
    days: Optional[int] = None
    format: str = "pdf"


SECTION_LABELS = {
    "overview":        "Overview Summary",
    "asset_health":    "Asset Health Breakdown",
    "critical_assets": "Critical & High Risk Assets",
    "pm_suggestions":  "PM Recommendations",
    "insights":        "AI Insights",
}
RISK_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean(val):
    if isinstance(val, float) and not math.isfinite(val):
        return None
    return val

def _fmt_prob(val) -> str:
    if val is None:
        return "—"
    return f"{float(val) * 100:.1f}%"

def _fmt_days(val) -> str:
    if val is None:
        return "—"
    try:
        return str(int(float(val)))
    except (TypeError, ValueError):
        return "—"

def _fmt_savings(val) -> str:
    if val is None:
        return "$0"
    return f"${float(val):,.0f}"

def _apply_date_filter(df, date_col: str, days: Optional[int]):
    if days and date_col in df.columns:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = df[df[date_col] >= cutoff]
    return df

def _dedup_predictions(df):
    if "prediction_date" in df.columns and "asset_id" in df.columns:
        df = df.sort_values("prediction_date", ascending=False)
        df = df.drop_duplicates(subset="asset_id", keep="first")
        df = df.sort_values("failure_probability", ascending=False)
    return df

def _fetch_data(sections: List[str], days: Optional[int], location_id: int) -> dict:
    data = {}
    if any(s in sections for s in ("overview", "asset_health", "critical_assets")):
        df = retrieve_failure_predictions(limit=10000, location_id=location_id)
        if not df.empty:
            df = _apply_date_filter(df, "prediction_date", days)
            df = _dedup_predictions(df)
        data["_predictions"] = (
            sorted(
                [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")],
                key=lambda r: RISK_ORDER.get(r.get("risk_level", "LOW"), 99),
            ) if not df.empty else []
        )
    if "pm_suggestions" in sections:
        df = retrieve_pm_optimization_suggestions(status=None, limit=10000, location_id=location_id)
        if not df.empty:
            df = _apply_date_filter(df, "suggestion_date", days)
        data["pm_suggestions"] = (
            [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]
            if not df.empty else []
        )
    if "insights" in sections:
        df = retrieve_maintenance_insights(limit=10000, location_id=location_id)
        if not df.empty:
            df = _apply_date_filter(df, "insight_date", days)
            df = df.drop_duplicates(subset="title", keep="first")
        data["insights"] = (
            [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]
            if not df.empty else []
        )
    return data

def _overview_stats(data: dict):
    preds = data.get("_predictions", [])
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for p in preds:
        rl = p.get("risk_level", "LOW")
        counts[rl] = counts.get(rl, 0) + 1
    scores = [p["failure_probability"] for p in preds if p.get("failure_probability") is not None]
    avg_score = round(sum(scores) / len(scores), 3) if scores else None
    return preds, counts, avg_score


# ── Logo PNG (shared by PDF canvas + XLSX) ─────────────────────────────────────

def _make_logo_png(scale: int = 4) -> io.BytesIO:
    """Render TrueSignal EKG waveform + dot as a transparent PNG using Pillow."""
    from PIL import Image, ImageDraw
    W, H = int(44 * scale), int(28 * scale)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pts = [(0,14),(8,14),(11,14),(14,3),(17,25),(20,14),(22,14),(44,14)]
    scaled = [(int(x * scale), int(y * scale)) for x, y in pts]
    lw = max(2, int(scale * 0.55))
    for i in range(len(scaled) - 1):
        draw.line([scaled[i], scaled[i+1]], fill=(99, 102, 241, 255), width=lw)
    cx, cy = int(14 * scale), int(3 * scale)
    r = max(2, int(2.5 * scale * 0.55))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(52, 211, 153, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ── PDF ────────────────────────────────────────────────────────────────────────

def _generate_pdf(sections: List[str], days: Optional[int], location_id: int) -> io.BytesIO:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    C = {k: colors.HexColor(v) for k, v in {
        "indigo":       INDIGO,
        "indigo_dark":  INDIGO_DARK,
        "indigo_light": INDIGO_LIGHT,
        "emerald":      EMERALD,
        "slate_50":     SLATE_50,
        "slate_100":    SLATE_100,
        "slate_200":    SLATE_200,
        "slate_700":    SLATE_700,
        "slate_900":    SLATE_900,
        "white":        WHITE,
        "red":    RISK_COLORS["CRITICAL"],
        "orange": RISK_COLORS["HIGH"],
        "amber":  RISK_COLORS["MEDIUM"],
        "green":  RISK_COLORS["LOW"],
    }.items()}
    RISK_C  = {k: colors.HexColor(v) for k, v in RISK_COLORS.items()}
    RISK_BC = {k: colors.HexColor(v) for k, v in RISK_BG.items()}

    PAGE_W, PAGE_H = letter
    HEADER_H = 0.85 * inch
    MARGIN_L = MARGIN_R = 0.75 * inch
    MARGIN_T = HEADER_H + 0.35 * inch
    MARGIN_B = 0.65 * inch
    CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R   # 504 pts

    styles = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    meta_sty    = ps("Meta",   fontSize=8,  textColor=C["slate_700"], spaceAfter=0)
    section_sty = ps("Sec",    fontSize=12, fontName="Helvetica-Bold",
                     textColor=C["slate_900"], spaceBefore=18, spaceAfter=6)
    body_sty    = ps("Body",   fontSize=8,  textColor=C["slate_700"], leading=12)
    cell_sty    = ps("Cell",   fontSize=8,  textColor=C["slate_700"], leading=11, wordWrap="LTR")
    hdr_cell    = ps("HCell",  fontSize=8,  fontName="Helvetica-Bold",
                     textColor=C["white"],   leading=11, wordWrap="LTR")
    risk_styles = {
        k: ps(f"Risk_{k}", fontSize=8, fontName="Helvetica-Bold",
              textColor=colors.HexColor(v), leading=11)
        for k, v in RISK_COLORS.items()
    }

    # ── Canvas header/footer drawn on every page ───────────────────────────────
    def _draw_page(canvas, doc):
        canvas.saveState()
        # Dark header band
        canvas.setFillColor(C["slate_900"])
        canvas.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)
        # Indigo accent line at bottom of band
        canvas.setFillColor(C["indigo"])
        canvas.rect(0, PAGE_H - HEADER_H - 1.5, PAGE_W, 1.5, fill=1, stroke=0)

        # EKG waveform drawn on canvas
        lx = MARGIN_L
        # Center the 28-unit-tall waveform vertically in the header
        base_y = PAGE_H - HEADER_H / 2 - (14 * 1.15)  # optical center
        sx = sy = 1.15  # scale factor
        ekg_pts = [(0,14),(8,14),(11,14),(14,3),(17,25),(20,14),(22,14),(44,14)]
        canvas.setStrokeColor(C["indigo"])
        canvas.setLineWidth(1.6)
        path = canvas.beginPath()
        for i, (x, y) in enumerate(ekg_pts):
            px = lx + x * sx
            py = base_y + (14 - y) * sy   # flip Y
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)
        canvas.drawPath(path, stroke=1, fill=0)
        # Emerald dot at peak (x=14, y=3 in SVG → highest point)
        dot_x = lx + 14 * sx
        dot_y = base_y + (14 - 3) * sy
        canvas.setFillColor(C["emerald"])
        canvas.circle(dot_x, dot_y, 2.8, fill=1, stroke=0)

        # Wordmark: "True" white + "Signal" emerald
        wx = lx + 44 * sx + 10
        wy = PAGE_H - HEADER_H / 2 + 3
        canvas.setFont("Helvetica-Bold", 15)
        canvas.setFillColor(C["white"])
        true_w = canvas.stringWidth("True", "Helvetica-Bold", 15)
        canvas.drawString(wx, wy, "True")
        canvas.setFillColor(C["emerald"])
        canvas.drawString(wx + true_w, wy, "Signal")
        # Subtitle
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor(INDIGO_LIGHT))
        canvas.drawString(wx, wy - 12, "MAINTENANCE INTELLIGENCE")

        # Right side: report metadata
        rx = PAGE_W - MARGIN_R
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(C["white"])
        canvas.drawRightString(rx, PAGE_H - HEADER_H / 2 + 3, "Maintenance Intelligence Report")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor(INDIGO_LIGHT))
        period_label = f"Last {days} days" if days else "All time"
        canvas.drawRightString(rx, PAGE_H - HEADER_H / 2 - 9, period_label)

        # Footer
        fy = MARGIN_B * 0.55
        canvas.setStrokeColor(C["slate_200"])
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_L, fy + 10, PAGE_W - MARGIN_R, fy + 10)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor(SLATE_700))
        canvas.drawString(MARGIN_L, fy, "TrueSignal · Maintenance Intelligence")
        canvas.setFillColor(colors.HexColor(SLATE_700))
        canvas.drawRightString(PAGE_W - MARGIN_R, fy, f"Page {doc.page}")

        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B * 1.4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
    )

    # ── Table builder ──────────────────────────────────────────────────────────
    BASE_TS = [
        ("BACKGROUND",    (0, 0), (-1,  0), C["indigo"]),
        ("TEXTCOLOR",     (0, 0), (-1,  0), C["white"]),
        ("FONTNAME",      (0, 0), (-1,  0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1,  0), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C["white"], C["slate_50"]]),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("GRID",          (0, 0), (-1, -1), 0.4, C["slate_200"]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("LINEBELOW",     (0, 0), (-1,  0), 1.5, C["indigo_dark"]),
    ]

    def make_table(rows, col_widths, extra=None):
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        ts = TableStyle(BASE_TS[:])
        for cmd in (extra or []):
            ts.add(*cmd)
        t.setStyle(ts)
        return t

    def P(text, sty=None):
        return Paragraph(str(text) if text is not None else "—", sty or cell_sty)

    def HP(text):
        return Paragraph(str(text), hdr_cell)

    def RP(text, level):
        return Paragraph(str(text), risk_styles.get(level, cell_sty))

    # ── Build story ────────────────────────────────────────────────────────────
    story = []
    gen_time = datetime.utcnow().strftime("%B %d, %Y  ·  %H:%M UTC")
    period_label = f"Last {days} days" if days else "All time"
    story.append(Paragraph(f"Generated {gen_time}  ·  Period: {period_label}", meta_sty))
    story.append(Spacer(1, 0.18 * inch))

    data = _fetch_data(sections, days, location_id)

    for section in sections:
        label = SECTION_LABELS.get(section, section)
        elems = [Paragraph(label, section_sty)]

        if section == "overview":
            preds, counts, avg_score = _overview_stats(data)
            rows = [
                [HP("Metric"), HP("Value"), HP("Note")],
                [P("Total Assets Monitored"), P(str(len(preds))), P("")],
                [P("Critical Risk"), RP(counts["CRITICAL"], "CRITICAL"), P("Immediate action required")],
                [P("High Risk"),     RP(counts["HIGH"],     "HIGH"),     P("Schedule within 30 days")],
                [P("Medium Risk"),   RP(counts["MEDIUM"],   "MEDIUM"),   P("Monitor closely")],
                [P("Low Risk (Safe)"), RP(counts["LOW"],    "LOW"),      P("On track")],
                [P("Avg Failure Probability"),
                 P(f"{avg_score * 100:.1f}%" if avg_score is not None else "—"), P("")],
            ]
            col_w = [CONTENT_W * 0.44, CONTENT_W * 0.18, CONTENT_W * 0.38]
            elems.append(make_table(rows, col_w))

        elif section in ("asset_health", "critical_assets"):
            preds = data.get("_predictions", [])
            if section == "critical_assets":
                preds = [p for p in preds if p.get("risk_level") in ("CRITICAL", "HIGH")]
            if preds:
                rows = [[HP("Asset ID"), HP("Risk"), HP("Fail Prob"),
                         HP("Days to Fail"), HP("Days Since PM"), HP("Reactive WOs")]]
                extra = []
                for ri, p in enumerate(preds, start=1):
                    rl = p.get("risk_level", "LOW")
                    rows.append([
                        P(p.get("asset_id", "")),
                        RP(rl, rl),
                        P(_fmt_prob(p.get("failure_probability"))),
                        P(_fmt_days(p.get("days_to_predicted_failure"))),
                        P(_fmt_days(p.get("days_since_last_pm"))),
                        P(str(p.get("reactive_work_count_90d") or 0)),
                    ])
                    extra += [
                        ("BACKGROUND", (0, ri), (-1, ri),
                         colors.HexColor(RISK_BG.get(rl, "#ffffff"))),
                    ]
                col_w = [
                    CONTENT_W * 0.24,
                    CONTENT_W * 0.13,
                    CONTENT_W * 0.13,
                    CONTENT_W * 0.15,
                    CONTENT_W * 0.19,
                    CONTENT_W * 0.16,
                ]
                elems.append(make_table(rows, col_w, extra))
            else:
                elems.append(Paragraph("No assets found for this period.", body_sty))

        elif section == "pm_suggestions":
            pms = data.get("pm_suggestions", [])
            if pms:
                rows = [[HP("Asset ID"), HP("Current PM"), HP("Suggested PM"),
                         HP("Est. Savings"), HP("Status")]]
                for p in pms:
                    curr = p.get("current_pm_frequency_days")
                    sugg = p.get("suggested_pm_frequency_days")
                    rows.append([
                        P(p.get("asset_id", "")),
                        P(f"{curr}d" if curr else "—"),
                        P(f"{sugg}d" if sugg else "—"),
                        P(_fmt_savings(p.get("estimated_cost_savings"))),
                        P((p.get("status") or "pending").title()),
                    ])
                col_w = [CONTENT_W*0.27, CONTENT_W*0.18, CONTENT_W*0.18,
                         CONTENT_W*0.19, CONTENT_W*0.18]
                elems.append(make_table(rows, col_w))
            else:
                elems.append(Paragraph("No PM recommendations available.", body_sty))

        elif section == "insights":
            ins = data.get("insights", [])
            if ins:
                rows = [[HP("Type"), HP("Title"), HP("Impact"), HP("Date")]]
                extra = []
                for ri, i in enumerate(ins, start=1):
                    impact = (i.get("impact_level") or "").title()
                    ic = colors.HexColor(IMPACT_COLORS.get(impact, SLATE_700))
                    rows.append([
                        P((i.get("insight_type") or "").replace("_", " ").title()),
                        P(i.get("title", "")),
                        Paragraph(impact, ps(f"Imp_{ri}", fontSize=8,
                                             fontName="Helvetica-Bold",
                                             textColor=ic, leading=11)),
                        P((i.get("insight_date") or "")[:10]),
                    ])
                col_w = [CONTENT_W*0.22, CONTENT_W*0.50, CONTENT_W*0.14, CONTENT_W*0.14]
                elems.append(make_table(rows, col_w))
            else:
                elems.append(Paragraph("No insights available.", body_sty))

        elems.append(Spacer(1, 0.12 * inch))
        story.append(KeepTogether(elems[:2]))  # keep section header + first element together
        story.extend(elems[2:])

    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    buf.seek(0)
    return buf


# ── XLSX ───────────────────────────────────────────────────────────────────────

def _generate_xlsx(sections: List[str], days: Optional[int], location_id: int) -> io.BytesIO:
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True, "remove_timezone": True})

    period_label = f"Last {days} days" if days else "All time"
    gen_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # ── Formats ────────────────────────────────────────────────────────────────
    def fmt(**kw):
        return wb.add_format(kw)

    cover_bg   = fmt(bg_color=SLATE_900, font_color=WHITE,
                     font_size=18, bold=True, valign="vcenter")
    cover_sub  = fmt(bg_color=SLATE_900, font_color=INDIGO_LIGHT,
                     font_size=9,  valign="vcenter")
    cover_meta = fmt(bg_color=SLATE_900, font_color="#94a3b8",
                     font_size=8,  valign="vcenter")
    cover_empty= fmt(bg_color=SLATE_900)

    col_hdr    = fmt(bg_color=INDIGO, font_color=WHITE, bold=True,
                     font_size=8, valign="vcenter", align="left",
                     border=1, border_color=INDIGO_DARK,
                     text_wrap=True)
    cell_base  = fmt(font_size=8, valign="vcenter", align="left",
                     border=1, border_color=SLATE_200, text_wrap=True)
    cell_alt   = fmt(font_size=8, valign="vcenter", align="left",
                     bg_color=SLATE_50, border=1, border_color=SLATE_200, text_wrap=True)
    cell_bold  = fmt(font_size=8, valign="vcenter", bold=True,
                     border=1, border_color=SLATE_200)

    section_hdr= fmt(bg_color=INDIGO_DARK, font_color=WHITE, bold=True,
                     font_size=10, valign="vcenter", left=5, border_color=INDIGO_DARK)
    spacer_fmt = fmt(bg_color="#f1f5f9")

    risk_fmts = {}
    risk_alt_fmts = {}
    for rl, color in RISK_COLORS.items():
        risk_fmts[rl] = fmt(
            font_color=color, bold=True, font_size=8,
            valign="vcenter", align="left",
            border=1, border_color=SLATE_200,
        )
        risk_alt_fmts[rl] = fmt(
            font_color=color, bold=True, font_size=8,
            valign="vcenter", align="left",
            bg_color=SLATE_50, border=1, border_color=SLATE_200,
        )

    impact_fmts = {}
    for level, color in IMPACT_COLORS.items():
        impact_fmts[level] = fmt(
            font_color=color, bold=True, font_size=8,
            valign="vcenter", align="left",
            border=1, border_color=SLATE_200,
        )

    savings_fmt = fmt(font_color=RISK_COLORS["LOW"], bold=True, font_size=8,
                      valign="vcenter", border=1, border_color=SLATE_200,
                      num_format='$#,##0')
    pct_fmt     = fmt(font_size=8, valign="vcenter", align="left",
                      border=1, border_color=SLATE_200)
    pct_alt_fmt = fmt(font_size=8, valign="vcenter", align="left",
                      bg_color=SLATE_50, border=1, border_color=SLATE_200)

    # ── Worksheet ──────────────────────────────────────────────────────────────
    ws = wb.add_worksheet("TrueSignal Report")
    ws.set_zoom(100)
    ws.hide_gridlines(2)
    ws.set_tab_color(INDIGO)

    # Print settings
    ws.set_paper(1)           # letter
    ws.set_landscape()
    ws.set_margins(left=0.75, right=0.75, top=0.75, bottom=0.75)
    ws.fit_to_pages(1, 0)     # fit to 1 page wide

    # ── Cover header (rows 0–4) ────────────────────────────────────────────────
    NUM_COLS = 8
    accent_fmt = fmt(bg_color=INDIGO, border=0)

    ws.set_row(0, 36)
    ws.merge_range(0, 0, 0, 1, "", cover_empty)
    ws.merge_range(0, 2, 0, NUM_COLS - 1,
                   "TrueSignal  ·  Maintenance Intelligence Report", cover_bg)

    ws.set_row(1, 16)
    ws.merge_range(1, 0, 1, 1, "", cover_empty)
    ws.merge_range(1, 2, 1, NUM_COLS - 1, "MAINTENANCE INTELLIGENCE PLATFORM", cover_sub)

    ws.set_row(2, 14)
    ws.merge_range(2, 0, 2, 1, "", cover_empty)
    ws.merge_range(2, 2, 2, NUM_COLS - 1,
                   f"Generated: {gen_time}  ·  Period: {period_label}", cover_meta)

    ws.set_row(3, 14)
    ws.merge_range(3, 0, 3, 1, "", cover_empty)
    ws.merge_range(3, 2, 3, NUM_COLS - 1, "truesignal.io", cover_meta)

    ws.set_row(4, 3)
    ws.merge_range(4, 0, 4, NUM_COLS - 1, "", accent_fmt)

    # Insert logo PNG into header
    try:
        logo_buf = _make_logo_png(scale=3)
        ws.insert_image(0, 0, "truesignal_logo.png", {
            "image_data": logo_buf,
            "x_offset": 8, "y_offset": 6,
            "x_scale": 0.9, "y_scale": 0.9,
            "object_position": 1,
        })
    except Exception:
        pass  # logo is cosmetic, don't fail report

    ROW = 5  # current write position
    data = _fetch_data(sections, days, location_id)

    def write_section_header(label):
        nonlocal ROW
        ws.set_row(ROW, 18)
        ws.merge_range(ROW, 0, ROW, NUM_COLS - 1, f"  {label.upper()}", section_hdr)
        ROW += 1

    def alt(row_idx):
        """Return True for alternating row shading."""
        return row_idx % 2 == 1

    for section in sections:
        label = SECTION_LABELS.get(section, section)
        ws.set_row(ROW, 4)
        ws.merge_range(ROW, 0, ROW, NUM_COLS - 1, "", spacer_fmt)
        ROW += 1

        write_section_header(label)

        if section == "overview":
            preds, counts, avg_score = _overview_stats(data)

            # Column widths for overview 3-col layout
            ws.set_column(0, 0, 32)
            ws.set_column(1, 1, 14)
            ws.set_column(2, 2, 28)

            # Header row
            ws.set_row(ROW, 16)
            ws.write(ROW, 0, "Metric",   col_hdr)
            ws.write(ROW, 1, "Value",    col_hdr)
            ws.write(ROW, 2, "Note",     col_hdr)
            ROW += 1

            rows_data = [
                ("Total Assets Monitored",  str(len(preds)),         ""),
                ("Critical Risk",           str(counts["CRITICAL"]), "Immediate action required"),
                ("High Risk",               str(counts["HIGH"]),     "Schedule within 30 days"),
                ("Medium Risk",             str(counts["MEDIUM"]),   "Monitor closely"),
                ("Low Risk (Safe)",         str(counts["LOW"]),      "On track"),
                ("Avg Failure Probability",
                 f"{avg_score*100:.1f}%" if avg_score else "—",     ""),
            ]
            risk_levels_ov = [None, "CRITICAL", "HIGH", "MEDIUM", "LOW", None]

            for i, (metric, val, note) in enumerate(rows_data):
                f0 = cell_alt if alt(i) else cell_base
                f1 = cell_alt if alt(i) else cell_base
                f2 = cell_alt if alt(i) else cell_base
                rl = risk_levels_ov[i]
                if rl:
                    f1 = risk_alt_fmts[rl] if alt(i) else risk_fmts[rl]
                ws.set_row(ROW, 15)
                ws.write(ROW, 0, metric, f0)
                ws.write(ROW, 1, str(val), f1)
                ws.write(ROW, 2, note, f2)
                ROW += 1

        elif section in ("asset_health", "critical_assets"):
            preds = data.get("_predictions", [])
            if section == "critical_assets":
                preds = [p for p in preds if p.get("risk_level") in ("CRITICAL", "HIGH")]

            ws.set_column(0, 0, 16)  # Asset ID
            ws.set_column(1, 1, 11)  # Risk
            ws.set_column(2, 2, 13)  # Fail Prob
            ws.set_column(3, 3, 13)  # Days to Fail
            ws.set_column(4, 4, 15)  # Days Since PM
            ws.set_column(5, 5, 14)  # Reactive WOs
            ws.set_column(6, 6, 40)  # Recommendation

            ws.set_row(ROW, 16)
            for ci, h in enumerate(["Asset ID", "Risk Level", "Fail Probability",
                                     "Days to Failure", "Days Since PM",
                                     "Reactive WOs (90d)", "Recommendation"]):
                ws.write(ROW, ci, h, col_hdr)
            ROW += 1

            if preds:
                for i, p in enumerate(preds):
                    rl = p.get("risk_level", "LOW")
                    f  = cell_alt if alt(i) else cell_base
                    rf = risk_alt_fmts[rl] if alt(i) else risk_fmts[rl]
                    pf = cell_alt if alt(i) else cell_base
                    ws.set_row(ROW, 14)
                    ws.write(ROW, 0, p.get("asset_id", ""),         f)
                    ws.write(ROW, 1, rl,                             rf)
                    ws.write(ROW, 2, _fmt_prob(p.get("failure_probability")), pf)
                    ws.write(ROW, 3, _fmt_days(p.get("days_to_predicted_failure")), f)
                    ws.write(ROW, 4, _fmt_days(p.get("days_since_last_pm")),   f)
                    ws.write(ROW, 5, p.get("reactive_work_count_90d") or 0,    f)
                    ws.write(ROW, 6, p.get("recommendation", ""),              f)
                    ROW += 1
            else:
                ws.write(ROW, 0, "No data available for this period.", cell_base)
                ROW += 1

        elif section == "pm_suggestions":
            pms = data.get("pm_suggestions", [])
            ws.set_column(0, 0, 16)
            ws.set_column(1, 1, 18)
            ws.set_column(2, 2, 18)
            ws.set_column(3, 3, 18)
            ws.set_column(4, 4, 14)
            ws.set_column(5, 5, 40)

            ws.set_row(ROW, 16)
            for ci, h in enumerate(["Asset ID", "Current PM Interval",
                                     "Suggested PM Interval", "Est. Annual Savings",
                                     "Status", "Reason"]):
                ws.write(ROW, ci, h, col_hdr)
            ROW += 1

            if pms:
                for i, p in enumerate(pms):
                    f  = cell_alt if alt(i) else cell_base
                    sf = savings_fmt
                    curr = p.get("current_pm_frequency_days")
                    sugg = p.get("suggested_pm_frequency_days")
                    ws.set_row(ROW, 14)
                    ws.write(ROW, 0, p.get("asset_id", ""),                    f)
                    ws.write(ROW, 1, f"{curr} days" if curr else "—",          f)
                    ws.write(ROW, 2, f"{sugg} days" if sugg else "—",          f)
                    sv = p.get("estimated_cost_savings")
                    ws.write_number(ROW, 3, float(sv) if sv else 0,            sf)
                    ws.write(ROW, 4, (p.get("status") or "pending").title(),   f)
                    ws.write(ROW, 5, p.get("reason", ""),                      f)
                    ROW += 1
            else:
                ws.write(ROW, 0, "No PM recommendations available.", cell_base)
                ROW += 1

        elif section == "insights":
            ins = data.get("insights", [])
            ws.set_column(0, 0, 20)
            ws.set_column(1, 1, 45)
            ws.set_column(2, 2, 30)
            ws.set_column(3, 3, 12)
            ws.set_column(4, 4, 12)

            ws.set_row(ROW, 16)
            for ci, h in enumerate(["Type", "Title", "Description", "Impact", "Date"]):
                ws.write(ROW, ci, h, col_hdr)
            ROW += 1

            if ins:
                for i, item in enumerate(ins):
                    f      = cell_alt if alt(i) else cell_base
                    impact = (item.get("impact_level") or "").title()
                    ifmt   = impact_fmts.get(impact, f)
                    itype  = (item.get("insight_type") or "").replace("_", " ").title()
                    ws.set_row(ROW, 14)
                    ws.write(ROW, 0, itype,                              f)
                    ws.write(ROW, 1, item.get("title", ""),              f)
                    ws.write(ROW, 2, item.get("description", ""),        f)
                    ws.write(ROW, 3, impact,                             ifmt)
                    ws.write(ROW, 4, (item.get("insight_date") or "")[:10], f)
                    ROW += 1
            else:
                ws.write(ROW, 0, "No insights available.", cell_base)
                ROW += 1

    # Freeze header rows (cover band)
    ws.freeze_panes(6, 0)

    wb.close()
    buf.seek(0)
    return buf


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/generate")
def generate_report(
    body: ReportRequest,
    location_id: int = Depends(_current_location),
):
    if not body.sections:
        raise HTTPException(400, "At least one section must be selected")
    if body.format not in ("xlsx", "pdf"):
        raise HTTPException(400, "Format must be 'xlsx' or 'pdf'")

    org_slug  = _get_org_name(location_id)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d-%H%M")
    filename  = f"truesignal-{org_slug}-{timestamp}.{body.format}"

    try:
        if body.format == "xlsx":
            buf = _generate_xlsx(body.sections, body.days, location_id)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            buf = _generate_pdf(body.sections, body.days, location_id)
            media_type = "application/pdf"
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Report generation failed: {exc}") from exc

    return Response(
        content=buf.getvalue(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
