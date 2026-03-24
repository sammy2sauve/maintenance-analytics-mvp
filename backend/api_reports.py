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
    report_type: str = "summary"   # "summary" | "full"


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

def _generate_pdf(sections: List[str], days: Optional[int], location_id: int) -> io.BytesIO:  # noqa: C901
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
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

    # ── Style helpers ──────────────────────────────────────────────────────────
    def P(text, sty):
        return Paragraph(str(text) if text is not None else "", sty)

    def section_heading(label):
        """Indigo left-bar section heading + thin rule below."""
        BAR_COL = 10   # left column width
        BAR_L   = 3    # leftPad for bar column → available = 10-3-0 = 7 (bar is 4pt)
        LBL_L   = 8    # leftPad for label column
        bar_cell = Table([[""]], colWidths=[4], rowHeights=[18])
        bar_cell.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), C["indigo"]),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))
        lbl = Paragraph(label.upper(), ps("SH", fontName="Helvetica-Bold",
                        fontSize=9, textColor=C["slate_900"],
                        spaceBefore=0, spaceAfter=0,
                        letterSpacing=0.8))
        t = Table([[bar_cell, lbl]], colWidths=[BAR_COL, CONTENT_W - BAR_COL])
        t.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(0,0),   BAR_L),
            ("LEFTPADDING",   (1,0),(1,0),   LBL_L),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))
        rule = HRFlowable(width="100%", thickness=0.5,
                          color=C["slate_200"], spaceAfter=8)
        return [Spacer(1, 0.2*inch), t, Spacer(1, 4), rule]

    def risk_bar_drawing(counts, total):
        """Horizontal stacked bar showing risk distribution."""
        W, H = CONTENT_W, 20
        d = Drawing(W, H)
        order  = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        clrs   = [colors.HexColor(RISK_COLORS[r]) for r in order]
        x = 0
        for rl, c in zip(order, clrs):
            cnt = counts.get(rl, 0)
            if cnt == 0 or total == 0:
                continue
            seg_w = (cnt / total) * W
            d.add(Rect(x, 0, seg_w, H, fillColor=c, strokeColor=None))
            if seg_w > 22:
                d.add(String(x + seg_w/2, H/2 - 3,
                             str(cnt),
                             fontSize=8, fontName="Helvetica-Bold",
                             fillColor=colors.white,
                             textAnchor="middle"))
            x += seg_w
        return d

    def prob_bar_drawing(prob, width=90, height=7):
        """Small horizontal fill bar for failure probability."""
        d = Drawing(width, height)
        d.add(Rect(0, 0, width, height,
                   fillColor=colors.HexColor("#e2e8f0"), strokeColor=None))
        if prob:
            rl = ("CRITICAL" if prob >= 0.75 else
                  "HIGH"     if prob >= 0.50 else
                  "MEDIUM"   if prob >= 0.25 else "LOW")
            fill_w = min(prob * width, width)
            d.add(Rect(0, 0, fill_w, height,
                       fillColor=colors.HexColor(RISK_COLORS[rl]),
                       strokeColor=None))
        return d

    def asset_entry(p, show_rec=True):
        """Single formatted asset entry — colored stripe, name, metrics, probability."""
        rl   = p.get("risk_level", "LOW")
        rc   = colors.HexColor(RISK_COLORS[rl])
        rbg  = colors.HexColor(RISK_BG.get(rl, "#f8fafc"))
        prob = p.get("failure_probability")

        # Explicit layout math: outer_col_w - left_pad - right_pad = inner_table_w
        _SW  = 5          # stripe width
        _RW  = 78         # right stats column width
        _MW  = CONTENT_W - _SW - _RW   # main column = 421
        _ML, _MR = 10, 6  # main cell padding
        _RL, _RR = 6, 8   # right cell padding
        _M_AV = _MW - _ML - _MR        # available inside main cell = 405
        _R_AV = _RW - _RL - _RR        # available inside right cell = 64
        _BADGE_W = 60

        # Left color stripe (zero padding so 5pt column stays positive)
        stripe = Table([[""]], colWidths=[_SW], rowHeights=[36])
        stripe.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), rc),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))

        id_sty   = ps("AID",   fontName="Helvetica-Bold", fontSize=9,
                      textColor=C["slate_900"], leading=12, spaceAfter=0)
        meta_sty = ps("AMeta", fontSize=7.5, textColor=C["slate_700"],
                      leading=10, spaceAfter=0)
        badge_sty= ps("ABadge",fontName="Helvetica-Bold", fontSize=7.5,
                      textColor=rc, leading=10, spaceAfter=0)
        rec_sty  = ps("ARec",  fontSize=7, textColor=colors.HexColor("#64748b"),
                      leading=9, spaceAfter=0)

        meta_parts = [
            f"{_fmt_days(p.get('days_since_last_pm'))}d since PM",
            f"{p.get('reactive_work_count_90d') or 0} reactive WOs",
        ]
        dtf_raw = p.get("days_to_predicted_failure")
        if dtf_raw is not None:
            try:
                dtf_int = int(float(dtf_raw))
                if dtf_int > 0:
                    meta_parts.insert(0, f"~{dtf_int}d to failure")
                # ≤0 means already at/past predicted failure — omit, risk level communicates urgency
            except (TypeError, ValueError):
                pass

        rec_text = (p.get("recommendation") or "").strip()
        main_rows = [
            [Paragraph(p.get("asset_id", ""), id_sty),   Paragraph(rl, badge_sty)],
            [Paragraph("  ·  ".join(meta_parts), meta_sty), ""],
        ]
        if show_rec and rec_text:
            trunc = rec_text[:140] + ("…" if len(rec_text) > 140 else "")
            main_rows.append([Paragraph(trunc, rec_sty), ""])

        spans = [("SPAN", (0,1),(1,1))]
        if show_rec and rec_text:
            spans.append(("SPAN", (0,2),(1,2)))
        inner = Table(main_rows, colWidths=[_M_AV - _BADGE_W, _BADGE_W])
        inner.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 1),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ] + spans))

        # Right: probability % + mini-bar + label
        prob_pct = Paragraph(
            _fmt_prob(prob),
            ps("PP", fontName="Helvetica-Bold", fontSize=11,
               textColor=rc, leading=13, spaceAfter=2, alignment=TA_CENTER)
        )
        prob_label = Paragraph("fail risk",
                               ps("PL", fontSize=6.5, textColor=C["slate_700"],
                                  leading=9, alignment=TA_CENTER))
        bar = prob_bar_drawing(prob or 0, width=_R_AV, height=5)

        right = Table(
            [[prob_pct], [bar], [prob_label]],
            colWidths=[_R_AV],
        )
        right.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 1),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))

        outer = Table([[stripe, inner, right]], colWidths=[_SW, _MW, _RW])
        outer.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), rbg),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            # stripe: zero padding (5pt col cannot absorb any padding)
            ("TOPPADDING",    (0,0),(0,0),   0),
            ("BOTTOMPADDING", (0,0),(0,0),   0),
            ("LEFTPADDING",   (0,0),(0,0),   0),
            ("RIGHTPADDING",  (0,0),(0,0),   0),
            # main content cell
            ("TOPPADDING",    (1,0),(1,0),   7),
            ("BOTTOMPADDING", (1,0),(1,0),   7),
            ("LEFTPADDING",   (1,0),(1,0),   _ML),
            ("RIGHTPADDING",  (1,0),(1,0),   _MR),
            # right stats cell
            ("TOPPADDING",    (2,0),(2,0),   7),
            ("BOTTOMPADDING", (2,0),(2,0),   7),
            ("LEFTPADDING",   (2,0),(2,0),   _RL),
            ("RIGHTPADDING",  (2,0),(2,0),   _RR),
            ("LINEBELOW",     (0,0),(-1,-1), 0.5, C["slate_200"]),
        ]))
        return outer

    def pm_entry(p, idx):
        """Formatted PM recommendation entry."""
        curr = p.get("current_pm_frequency_days")
        sugg = p.get("suggested_pm_frequency_days")
        status = (p.get("status") or "pending").title()
        status_color = (colors.HexColor(RISK_COLORS["LOW"])
                        if status == "Implemented"
                        else colors.HexColor(RISK_COLORS["MEDIUM"]))

        # Explicit dimension math
        _STAT_W = 80
        _MAIN_W = CONTENT_W - _STAT_W   # = 424
        _ML, _MR = 10, 6
        _SL, _SR = 6, 8
        _MAIN_AV = _MAIN_W - _ML - _MR   # = 408
        _STAT_AV = _STAT_W - _SL - _SR   # = 66

        asset_sty  = ps("PMasset", fontName="Helvetica-Bold", fontSize=9,
                         textColor=C["slate_900"], leading=12)
        freq_sty   = ps("PMfreq",  fontSize=8, textColor=C["slate_700"], leading=11)
        stat_sty   = ps("PMstat",  fontName="Helvetica-Bold", fontSize=7.5,
                         textColor=status_color, leading=10)
        reason_sty = ps("PMreason",fontSize=7.5, textColor=C["slate_700"], leading=10)

        freq_text = (f"Every {curr}d  →  Every {sugg}d"
                     if curr and sugg else "Interval adjustment recommended")
        reason = (p.get("reason") or "")

        left = Table(
            [[Paragraph(p.get("asset_id", ""), asset_sty)],
             [Paragraph(freq_text, freq_sty)],
             [Paragraph(reason[:120] + ("…" if len(reason) > 120 else ""), reason_sty)]],
            colWidths=[_MAIN_AV],
        )
        left.setStyle(TableStyle([
            ("TOPPADDING",    (0,0),(-1,-1), 1),
            ("BOTTOMPADDING", (0,0),(-1,-1), 1),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))

        right = Table([[Paragraph(status, stat_sty)]], colWidths=[_STAT_AV])
        right.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 1),
            ("BOTTOMPADDING", (0,0),(-1,-1), 1),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))

        bg = C["slate_50"] if idx % 2 else colors.white
        outer = Table([[left, right]], colWidths=[_MAIN_W, _STAT_W])
        outer.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bg),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(0,0),   _ML),
            ("RIGHTPADDING",  (0,0),(0,0),   _MR),
            ("LEFTPADDING",   (1,0),(1,0),   _SL),
            ("RIGHTPADDING",  (1,0),(1,0),   _SR),
            ("LINEBELOW",     (0,0),(-1,-1), 0.5, C["slate_200"]),
        ]))
        return outer

    def insight_entry(item, idx):
        """Card-style insight entry with impact color strip."""
        impact = (item.get("impact_level") or "Low").title()
        ic     = colors.HexColor(IMPACT_COLORS.get(impact, SLATE_700))
        itype  = (item.get("insight_type") or "").replace("_", " ").title()
        bg     = C["slate_50"] if idx % 2 else colors.white

        # Explicit dimension math
        _SW = 5          # stripe width
        _BW = CONTENT_W - _SW   # body column = 499
        _BL, _BR = 10, 8
        _B_AV = _BW - _BL - _BR  # available inside body cell = 481

        stripe = Table([[""]], colWidths=[_SW], rowHeights=[44])
        stripe.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), ic),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))

        type_sty  = ps("IT",  fontSize=7, textColor=ic,
                        fontName="Helvetica-Bold", leading=9)
        title_sty = ps("ITl", fontSize=9, fontName="Helvetica-Bold",
                        textColor=C["slate_900"], leading=12, spaceAfter=2)
        desc_sty  = ps("IDs", fontSize=7.5, textColor=C["slate_700"], leading=10)
        date_sty  = ps("IDt", fontSize=7, textColor=colors.HexColor("#94a3b8"),
                        leading=9)

        desc = item.get("description", item.get("title", ""))
        body = Table(
            [[Paragraph(itype.upper(), type_sty)],
             [Paragraph(item.get("title", ""), title_sty)],
             [Paragraph(desc[:160] + ("…" if len(desc) > 160 else ""), desc_sty)],
             [Paragraph((item.get("insight_date") or "")[:10], date_sty)]],
            colWidths=[_B_AV],
        )
        body.setStyle(TableStyle([
            ("TOPPADDING",    (0,0),(-1,-1), 1),
            ("BOTTOMPADDING", (0,0),(-1,-1), 1),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))

        outer = Table([[stripe, body]], colWidths=[_SW, _BW])
        outer.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bg),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            # stripe: zero padding
            ("TOPPADDING",    (0,0),(0,0),   0),
            ("BOTTOMPADDING", (0,0),(0,0),   0),
            ("LEFTPADDING",   (0,0),(0,0),   0),
            ("RIGHTPADDING",  (0,0),(0,0),   0),
            # body cell
            ("TOPPADDING",    (1,0),(1,0),   8),
            ("BOTTOMPADDING", (1,0),(1,0),   8),
            ("LEFTPADDING",   (1,0),(1,0),   _BL),
            ("RIGHTPADDING",  (1,0),(1,0),   _BR),
            ("LINEBELOW",     (0,0),(-1,-1), 0.5, C["slate_200"]),
        ]))
        return outer

    # ── Build story ────────────────────────────────────────────────────────────
    story = []
    gen_time = datetime.utcnow().strftime("%B %d, %Y  ·  %H:%M UTC")
    period_label = f"Last {days} days" if days else "All time"
    story.append(Paragraph(
        f"Generated {gen_time}  ·  Period: {period_label}",
        ps("Meta", fontSize=8, textColor=C["slate_700"])
    ))
    story.append(Spacer(1, 0.05 * inch))

    data = _fetch_data(sections, days, location_id)

    for section in sections:

        # ── Overview ──────────────────────────────────────────────────────────
        if section == "overview":
            preds, counts, avg_score = _overview_stats(data)
            total = len(preds)

            story.extend(section_heading("Overview Summary"))

            # KPI card grid: 4 risk counts across full width
            # Math: kpi_grid cellPad=2 → cell avail = CARD_W-4
            #       card cellPad=4 → card_inner avail = (CARD_W-4)-8 = CARD_W-12
            CARD_W      = CONTENT_W / 4          # = 126
            GRID_PAD    = 2
            CARD_PAD    = 4
            CARD_CELL_W = CARD_W - GRID_PAD * 2  # = 122
            CARD_INN_W  = CARD_CELL_W - CARD_PAD * 2  # = 114

            kpi_rows = [[]]
            for rl in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                cnt     = counts[rl]
                fg      = colors.HexColor(RISK_COLORS[rl])
                bg      = colors.HexColor(RISK_BG[rl])
                num_sty = ps(f"KN_{rl}", fontName="Helvetica-Bold", fontSize=28,
                              textColor=fg, leading=30, alignment=TA_CENTER)
                lbl_sty = ps(f"KL_{rl}", fontSize=7.5, textColor=C["slate_700"],
                              leading=10, alignment=TA_CENTER,
                              fontName="Helvetica-Bold")
                sub_sty = ps(f"KS_{rl}", fontSize=7, textColor=colors.HexColor("#94a3b8"),
                              leading=9, alignment=TA_CENTER)
                card_inner = Table(
                    [[Paragraph(str(cnt), num_sty)],
                     [Paragraph(rl, lbl_sty)],
                     [Paragraph("Assets", sub_sty)]],
                    colWidths=[CARD_INN_W],
                )
                card_inner.setStyle(TableStyle([
                    ("TOPPADDING",    (0,0),(-1,-1), 2),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 2),
                    ("LEFTPADDING",   (0,0),(-1,-1), 0),
                    ("RIGHTPADDING",  (0,0),(-1,-1), 0),
                ]))
                card = Table([[card_inner]], colWidths=[CARD_CELL_W])
                card.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0),(-1,-1), bg),
                    ("TOPPADDING",    (0,0),(-1,-1), 12),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 12),
                    ("LEFTPADDING",   (0,0),(-1,-1), CARD_PAD),
                    ("RIGHTPADDING",  (0,0),(-1,-1), CARD_PAD),
                    ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor(RISK_COLORS[rl] + "40"
                                                           if len(RISK_COLORS[rl]) == 7
                                                           else RISK_COLORS[rl])),
                ]))
                kpi_rows[0].append(card)

            kpi_grid = Table(kpi_rows, colWidths=[CARD_W] * 4, rowHeights=[None])
            kpi_grid.setStyle(TableStyle([
                ("TOPPADDING",    (0,0),(-1,-1), 0),
                ("BOTTOMPADDING", (0,0),(-1,-1), 0),
                ("LEFTPADDING",   (0,0),(-1,-1), GRID_PAD),
                ("RIGHTPADDING",  (0,0),(-1,-1), GRID_PAD),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ]))
            story.append(kpi_grid)
            story.append(Spacer(1, 0.12 * inch))

            # Two secondary stats
            # Math: stats_row cellPad L=12 R=8 → stat_block avail = CONTENT_W/2 - 20
            prob_str    = f"{avg_score * 100:.1f}%" if avg_score else "—"
            HALF_W      = CONTENT_W / 2
            STAT_L, STAT_R = 12, 8
            STAT_INN_W  = HALF_W - STAT_L - STAT_R   # = 232
            big_sty  = ps("Big2", fontName="Helvetica-Bold", fontSize=14,
                           textColor=C["indigo"], leading=16)
            lbl2_sty = ps("Lbl2", fontSize=7.5, textColor=C["slate_700"],
                           leading=10, fontName="Helvetica-Bold")

            def stat_block(big, label):
                t = Table(
                    [[Paragraph(big, big_sty)],
                     [Paragraph(label, lbl2_sty)]],
                    colWidths=[STAT_INN_W],
                )
                t.setStyle(TableStyle([
                    ("TOPPADDING",    (0,0),(-1,-1), 2),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 2),
                    ("LEFTPADDING",   (0,0),(-1,-1), 0),
                    ("RIGHTPADDING",  (0,0),(-1,-1), 0),
                ]))
                return t

            stats_row = Table(
                [[stat_block(str(total), "Total Assets Monitored"),
                  stat_block(prob_str,   "Avg Failure Probability")]],
                colWidths=[HALF_W, HALF_W],
            )
            stats_row.setStyle(TableStyle([
                ("TOPPADDING",    (0,0),(-1,-1), 6),
                ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                ("LEFTPADDING",   (0,0),(0,0),   STAT_L),
                ("RIGHTPADDING",  (0,0),(0,0),   STAT_R),
                ("LEFTPADDING",   (1,0),(1,0),   STAT_L),
                ("RIGHTPADDING",  (1,0),(1,0),   STAT_R),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                ("LINEBEFORE",    (1,0),(1,-1),  0.5, C["slate_200"]),
            ]))
            story.append(stats_row)
            story.append(Spacer(1, 0.1 * inch))

            # Risk distribution bar
            if total > 0:
                bar_label = ps("BL", fontSize=7, textColor=C["slate_700"],
                                leading=9, spaceAfter=3)
                story.append(Paragraph("RISK DISTRIBUTION", bar_label))
                story.append(risk_bar_drawing(counts, total))
                # Legend
                legend_items = []
                for rl in ["CRITICAL","HIGH","MEDIUM","LOW"]:
                    cnt = counts[rl]
                    fg  = colors.HexColor(RISK_COLORS[rl])
                    legend_items.append(Paragraph(
                        f"<font color='{RISK_COLORS[rl]}'><b>■</b></font> {rl} ({cnt})",
                        ps(f"Leg_{rl}", fontSize=7, textColor=C["slate_700"],
                           leading=9, spaceAfter=0)
                    ))
                leg_row = Table([legend_items], colWidths=[CONTENT_W/4]*4)
                leg_row.setStyle(TableStyle([
                    ("TOPPADDING",    (0,0),(-1,-1), 4),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 0),
                    ("LEFTPADDING",   (0,0),(-1,-1), 4),
                    ("RIGHTPADDING",  (0,0),(-1,-1), 0),
                ]))
                story.append(leg_row)

        # ── Asset Health / Critical ────────────────────────────────────────────
        elif section in ("asset_health", "critical_assets"):
            label = SECTION_LABELS[section]
            preds = data.get("_predictions", [])
            if section == "critical_assets":
                preds = [p for p in preds if p.get("risk_level") in ("CRITICAL","HIGH")]
            story.extend(section_heading(label))
            if preds:
                for p in preds:
                    story.append(asset_entry(p))
                story.append(Spacer(1, 0.04 * inch))
            else:
                story.append(Paragraph(
                    "No assets at this risk level for the selected period.",
                    ps("NA", fontSize=8, textColor=C["slate_700"])
                ))

        # ── PM Suggestions ────────────────────────────────────────────────────
        elif section == "pm_suggestions":
            pms = data.get("pm_suggestions", [])
            story.extend(section_heading("PM Recommendations"))
            if pms:
                for i, p in enumerate(pms):
                    story.append(pm_entry(p, i))
                story.append(Spacer(1, 0.04 * inch))
            else:
                story.append(Paragraph(
                    "No PM recommendations available.",
                    ps("NA2", fontSize=8, textColor=C["slate_700"])
                ))

        # ── Insights ─────────────────────────────────────────────────────────
        elif section == "insights":
            ins = data.get("insights", [])
            story.extend(section_heading("AI Insights"))
            if ins:
                for i, item in enumerate(ins):
                    story.append(insight_entry(item, i))
                story.append(Spacer(1, 0.04 * inch))
            else:
                story.append(Paragraph(
                    "No insights available.",
                    ps("NA3", fontSize=8, textColor=C["slate_700"])
                ))

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
            ws.set_column(1, 1, 20)
            ws.set_column(2, 2, 20)
            ws.set_column(3, 3, 14)
            ws.set_column(4, 4, 48)

            ws.set_row(ROW, 16)
            for ci, h in enumerate(["Asset ID", "Current PM Interval",
                                     "Suggested PM Interval", "Status", "Reason"]):
                ws.write(ROW, ci, h, col_hdr)
            ROW += 1

            if pms:
                for i, p in enumerate(pms):
                    f    = cell_alt if alt(i) else cell_base
                    curr = p.get("current_pm_frequency_days")
                    sugg = p.get("suggested_pm_frequency_days")
                    ws.set_row(ROW, 14)
                    ws.write(ROW, 0, p.get("asset_id", ""),                   f)
                    ws.write(ROW, 1, f"{curr} days" if curr else "—",         f)
                    ws.write(ROW, 2, f"{sugg} days" if sugg else "—",         f)
                    ws.write(ROW, 3, (p.get("status") or "pending").title(),  f)
                    ws.write(ROW, 4, p.get("reason", ""),                     f)
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


# ── One-page summary PDF ───────────────────────────────────────────────────────

def _generate_summary_pdf(sections: List[str], days: Optional[int], location_id: int) -> io.BytesIO:
    """Single-page maintenance health summary — executive overview."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    C = {k: colors.HexColor(v) for k, v in {
        "indigo": INDIGO, "indigo_dark": INDIGO_DARK, "indigo_light": INDIGO_LIGHT,
        "emerald": EMERALD, "slate_50": SLATE_50, "slate_100": SLATE_100,
        "slate_200": SLATE_200, "slate_700": SLATE_700, "slate_900": SLATE_900,
        "white": WHITE,
    }.items()}

    PAGE_W, PAGE_H = letter
    HEADER_H = 0.85 * inch
    MARGIN_L = MARGIN_R = 0.75 * inch
    MARGIN_T = HEADER_H + 0.35 * inch
    MARGIN_B = 0.65 * inch
    CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

    styles = getSampleStyleSheet()
    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    period_label = f"Last {days} days" if days else "All time"

    def _draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C["slate_900"])
        canvas.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)
        canvas.setFillColor(C["indigo"])
        canvas.rect(0, PAGE_H - HEADER_H - 1.5, PAGE_W, 1.5, fill=1, stroke=0)
        lx = MARGIN_L
        base_y = PAGE_H - HEADER_H / 2 - (14 * 1.15)
        sx = sy = 1.15
        ekg_pts = [(0,14),(8,14),(11,14),(14,3),(17,25),(20,14),(22,14),(44,14)]
        canvas.setStrokeColor(C["indigo"])
        canvas.setLineWidth(1.6)
        path = canvas.beginPath()
        for i, (x, y) in enumerate(ekg_pts):
            px = lx + x * sx
            py = base_y + (14 - y) * sy
            if i == 0: path.moveTo(px, py)
            else:       path.lineTo(px, py)
        canvas.drawPath(path, stroke=1, fill=0)
        canvas.setFillColor(C["emerald"])
        canvas.circle(lx + 14*sx, base_y + (14-3)*sy, 2.8, fill=1, stroke=0)
        wx = lx + 44*sx + 10
        wy = PAGE_H - HEADER_H/2 + 3
        canvas.setFont("Helvetica-Bold", 15)
        canvas.setFillColor(C["white"])
        true_w = canvas.stringWidth("True", "Helvetica-Bold", 15)
        canvas.drawString(wx, wy, "True")
        canvas.setFillColor(C["emerald"])
        canvas.drawString(wx + true_w, wy, "Signal")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor(INDIGO_LIGHT))
        canvas.drawString(wx, wy - 12, "MAINTENANCE INTELLIGENCE")
        rx = PAGE_W - MARGIN_R
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(C["white"])
        canvas.drawRightString(rx, PAGE_H - HEADER_H/2 + 3, "Maintenance Health Summary")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor(INDIGO_LIGHT))
        canvas.drawRightString(rx, PAGE_H - HEADER_H/2 - 9, period_label)
        fy = MARGIN_B * 0.55
        canvas.setStrokeColor(C["slate_200"])
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_L, fy + 10, PAGE_W - MARGIN_R, fy + 10)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor(SLATE_700))
        canvas.drawString(MARGIN_L, fy, "TrueSignal · Maintenance Intelligence")
        canvas.drawRightString(PAGE_W - MARGIN_R, fy, "Executive Summary")
        canvas.restoreState()

    # ── Fetch data ─────────────────────────────────────────────────────────────
    data = _fetch_data(
        ["overview", "asset_health", "pm_suggestions", "insights"],
        days, location_id
    )
    preds, counts, avg_score = _overview_stats(data)
    total = len(preds)
    urgent = [p for p in preds if p.get("risk_level") in ("CRITICAL", "HIGH")][:5]
    pms    = data.get("pm_suggestions", [])[:4]
    ins    = data.get("insights", [])[:3]

    # ── Shared styles ──────────────────────────────────────────────────────────
    meta_sty  = ps("SM",  fontSize=8,  textColor=C["slate_700"])
    sh_sty    = ps("SSH", fontSize=8,  fontName="Helvetica-Bold",
                   textColor=C["slate_900"], letterSpacing=0.8)
    tbl_h_sty = ps("STH", fontSize=7.5, fontName="Helvetica-Bold",
                   textColor=C["white"], leading=10)
    cell_sty  = ps("STC", fontSize=7.5, textColor=C["slate_700"],  leading=10)
    bold_sty  = ps("STCB",fontSize=7.5, fontName="Helvetica-Bold",
                   textColor=C["slate_900"], leading=10)
    dim_sty   = ps("STD", fontSize=7,   textColor=colors.HexColor("#94a3b8"), leading=9)

    # ── Table style helpers ────────────────────────────────────────────────────
    HDR_TS = TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  C["indigo"]),
        ("TEXTCOLOR",     (0,0),(-1,0),  C["white"]),
        ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0),  7.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C["white"], C["slate_50"]]),
        ("FONTSIZE",      (0,1),(-1,-1), 7.5),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("LINEBELOW",     (0,0),(-1,0),  1, C["indigo_dark"]),
        ("LINEBELOW",     (0,1),(-1,-1), 0.4, C["slate_200"]),
    ])

    def compact_heading(label):
        bar = Table([[""]], colWidths=[4], rowHeights=[14])
        bar.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), C["indigo"]),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))
        t = Table([[bar, Paragraph(label.upper(), sh_sty)]], colWidths=[10, CONTENT_W - 10])
        t.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(0,0),   3),
            ("LEFTPADDING",   (1,0),(1,0),   7),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))
        return [Spacer(1, 10), t, Spacer(1, 4),
                HRFlowable(width="100%", thickness=0.5, color=C["slate_200"], spaceAfter=6)]

    # ── Build story ────────────────────────────────────────────────────────────
    story = []

    gen_time = datetime.utcnow().strftime("%B %d, %Y  ·  %H:%M UTC")
    story.append(Paragraph(
        f"Generated {gen_time}  ·  Period: {period_label}",
        meta_sty
    ))
    story.append(Spacer(1, 10))

    # ── Fleet Health ──────────────────────────────────────────────────────────
    story.extend(compact_heading("Fleet Health Overview"))

    # KPI cards: compact 4-across
    # Math: CARD_W=CONTENT_W/4, grid pad=2, card pad=4 → inner=CARD_W-12
    CARD_W    = CONTENT_W / 4
    G_PAD     = 2
    C_PAD     = 4
    C_CELL_W  = CARD_W - G_PAD * 2
    C_INN_W   = C_CELL_W - C_PAD * 2

    kpi_cells = []
    for rl in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        cnt = counts[rl]
        fg  = colors.HexColor(RISK_COLORS[rl])
        bg  = colors.HexColor(RISK_BG[rl])
        num = Paragraph(str(cnt), ps(f"KN_{rl}", fontName="Helvetica-Bold", fontSize=22,
                                      textColor=fg, leading=24, alignment=TA_CENTER))
        lbl = Paragraph(rl, ps(f"KL_{rl}", fontSize=7, fontName="Helvetica-Bold",
                                textColor=C["slate_700"], leading=9, alignment=TA_CENTER))
        inn = Table([[num],[lbl]], colWidths=[C_INN_W])
        inn.setStyle(TableStyle([
            ("TOPPADDING",    (0,0),(-1,-1), 1),
            ("BOTTOMPADDING", (0,0),(-1,-1), 1),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))
        card = Table([[inn]], colWidths=[C_CELL_W])
        card.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bg),
            ("TOPPADDING",    (0,0),(-1,-1), 10),
            ("BOTTOMPADDING", (0,0),(-1,-1), 10),
            ("LEFTPADDING",   (0,0),(-1,-1), C_PAD),
            ("RIGHTPADDING",  (0,0),(-1,-1), C_PAD),
            ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor(RISK_COLORS[rl] + "40"
                                                   if len(RISK_COLORS[rl]) == 7
                                                   else RISK_COLORS[rl])),
        ]))
        kpi_cells.append(card)

    grid = Table([kpi_cells], colWidths=[CARD_W]*4)
    grid.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
        ("LEFTPADDING",   (0,0),(-1,-1), G_PAD),
        ("RIGHTPADDING",  (0,0),(-1,-1), G_PAD),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(grid)
    story.append(Spacer(1, 8))

    # Stats row
    prob_str = f"{avg_score*100:.1f}%" if avg_score else "—"
    HALF_W   = CONTENT_W / 2
    SL = SR  = 10
    S_INN    = HALF_W - SL - SR

    def stat_pair(big, label):
        t = Table(
            [[Paragraph(big,   ps(f"SB_{big}", fontName="Helvetica-Bold", fontSize=13,
                                   textColor=C["indigo"], leading=15))],
             [Paragraph(label, ps(f"SL_{label}", fontSize=7, textColor=C["slate_700"],
                                   fontName="Helvetica-Bold", leading=9))]],
            colWidths=[S_INN],
        )
        t.setStyle(TableStyle([
            ("TOPPADDING",    (0,0),(-1,-1), 1),
            ("BOTTOMPADDING", (0,0),(-1,-1), 1),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))
        return t

    stats = Table(
        [[stat_pair(str(total), "Total Assets Monitored"),
          stat_pair(prob_str,   "Avg Failure Probability")]],
        colWidths=[HALF_W, HALF_W],
    )
    stats.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(0,0),   SL),
        ("RIGHTPADDING",  (0,0),(0,0),   SR),
        ("LEFTPADDING",   (1,0),(1,0),   SL),
        ("RIGHTPADDING",  (1,0),(1,0),   SR),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LINEBEFORE",    (1,0),(1,-1),  0.5, C["slate_200"]),
    ]))
    story.append(stats)
    story.append(Spacer(1, 6))

    # Risk distribution bar
    if total > 0:
        bar_lbl = ps("SBL", fontSize=7, textColor=C["slate_700"], leading=9, spaceAfter=2)
        story.append(Paragraph("RISK DISTRIBUTION", bar_lbl))
        W, H = CONTENT_W, 16
        d = Drawing(W, H)
        x = 0
        for rl in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            cnt = counts.get(rl, 0)
            if cnt == 0 or total == 0: continue
            seg_w = (cnt / total) * W
            d.add(Rect(x, 0, seg_w, H, fillColor=colors.HexColor(RISK_COLORS[rl]), strokeColor=None))
            if seg_w > 20:
                d.add(String(x + seg_w/2, H/2 - 3, str(cnt),
                             fontSize=7, fontName="Helvetica-Bold",
                             fillColor=colors.white, textAnchor="middle"))
            x += seg_w
        story.append(d)
        leg_items = [
            Paragraph(f"<font color='{RISK_COLORS[rl]}'><b>■</b></font> {rl} ({counts[rl]})",
                      ps(f"SLeg_{rl}", fontSize=6.5, textColor=C["slate_700"], leading=9))
            for rl in ["CRITICAL","HIGH","MEDIUM","LOW"]
        ]
        leg = Table([leg_items], colWidths=[CONTENT_W/4]*4)
        leg.setStyle(TableStyle([
            ("TOPPADDING",    (0,0),(-1,-1), 3),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))
        story.append(leg)

    # ── Urgent Attention ──────────────────────────────────────────────────────
    story.extend(compact_heading("Urgent Attention"))

    if urgent:
        # Col widths: asset_id | risk | fail% | since_pm | action
        # Sum must = CONTENT_W with padding absorbed by table
        # Table has L=6, R=6 padding per cell → subtract from colWidths
        _CW = [90, 48, 46, 60, CONTENT_W - 90 - 48 - 46 - 60]  # last col fills rest = 220
        rows = [["Asset ID", "Risk", "Fail %", "Since PM", "Recommendation"]]
        for p in urgent:
            rl  = p.get("risk_level", "LOW")
            rec = (p.get("recommendation") or "").strip()
            rows.append([
                p.get("asset_id", ""),
                rl,
                _fmt_prob(p.get("failure_probability")),
                f"{_fmt_days(p.get('days_since_last_pm'))}d",
                rec[:80] + ("…" if len(rec) > 80 else ""),
            ])
        t = Table(rows, colWidths=_CW, repeatRows=1)
        ts = TableStyle(list(HDR_TS._cmds))
        # Risk column coloring
        for ri, p in enumerate(urgent, start=1):
            rl = p.get("risk_level", "LOW")
            ts.add("TEXTCOLOR", (1, ri), (1, ri), colors.HexColor(RISK_COLORS[rl]))
            ts.add("FONTNAME",  (1, ri), (1, ri), "Helvetica-Bold")
        t.setStyle(ts)
        story.append(t)
    else:
        story.append(Paragraph("No critical or high-risk assets.", ps("SNone", fontSize=8, textColor=C["slate_700"])))

    # ── PM Recommendations ────────────────────────────────────────────────────
    story.extend(compact_heading("PM Schedule Recommendations"))

    if pms:
        _PW = [90, 100, 55, CONTENT_W - 90 - 100 - 55]   # last col fills = 259
        pm_rows = [["Asset ID", "Schedule Change", "Status", "Reason"]]
        for p in pms:
            curr = p.get("current_pm_frequency_days")
            sugg = p.get("suggested_pm_frequency_days")
            freq = (f"{curr}d → {sugg}d" if curr and sugg else "Adjust interval")
            reason = (p.get("reason") or "")
            status = (p.get("status") or "pending").title()
            pm_rows.append([
                p.get("asset_id", ""),
                freq,
                status,
                reason[:70] + ("…" if len(reason) > 70 else ""),
            ])
        t = Table(pm_rows, colWidths=_PW, repeatRows=1)
        ts = TableStyle(list(HDR_TS._cmds))
        for ri, p in enumerate(pms, start=1):
            status = (p.get("status") or "pending").title()
            sc = colors.HexColor(RISK_COLORS["LOW"] if status == "Implemented" else RISK_COLORS["MEDIUM"])
            ts.add("TEXTCOLOR", (2, ri), (2, ri), sc)
            ts.add("FONTNAME",  (2, ri), (2, ri), "Helvetica-Bold")
        t.setStyle(ts)
        story.append(t)
    else:
        story.append(Paragraph("No PM recommendations available.", ps("SNone2", fontSize=8, textColor=C["slate_700"])))

    # ── AI Insights ───────────────────────────────────────────────────────────
    story.extend(compact_heading("Key Insights"))

    if ins:
        for item in ins:
            impact = (item.get("impact_level") or "Low").title()
            ic     = colors.HexColor(IMPACT_COLORS.get(impact, SLATE_700))
            itype  = (item.get("insight_type") or "").replace("_", " ").title()
            title  = item.get("title", "")
            desc   = (item.get("description") or "").strip()
            text   = f"<b>{title}</b>"
            if desc and desc != title:
                short = desc[:100] + ("…" if len(desc) > 100 else "")
                text += f" — {short}"
            type_p  = Paragraph(itype.upper(), ps(f"SIT_{itype}", fontSize=6.5,
                                  fontName="Helvetica-Bold", textColor=ic, leading=9))
            body_p  = Paragraph(text, ps(f"SIB_{title[:10]}", fontSize=7.5,
                                  textColor=C["slate_700"], leading=10))
            # _SW=5, _BL=8, _BR=6, _BW=CONTENT_W-5, _B_AV=CONTENT_W-5-8-6=485
            _SW, _BL, _BR = 5, 8, 6
            _BW   = CONTENT_W - _SW
            _B_AV = _BW - _BL - _BR
            stripe = Table([[""]], colWidths=[_SW], rowHeights=[26])
            stripe.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), ic),
                ("TOPPADDING",    (0,0),(-1,-1), 0),
                ("BOTTOMPADDING", (0,0),(-1,-1), 0),
                ("LEFTPADDING",   (0,0),(-1,-1), 0),
                ("RIGHTPADDING",  (0,0),(-1,-1), 0),
            ]))
            body_tbl = Table([[type_p],[body_p]], colWidths=[_B_AV])
            body_tbl.setStyle(TableStyle([
                ("TOPPADDING",    (0,0),(-1,-1), 1),
                ("BOTTOMPADDING", (0,0),(-1,-1), 1),
                ("LEFTPADDING",   (0,0),(-1,-1), 0),
                ("RIGHTPADDING",  (0,0),(-1,-1), 0),
            ]))
            row = Table([[stripe, body_tbl]], colWidths=[_SW, _BW])
            row.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), C["slate_50"]),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                ("TOPPADDING",    (0,0),(0,0),   0),
                ("BOTTOMPADDING", (0,0),(0,0),   0),
                ("LEFTPADDING",   (0,0),(0,0),   0),
                ("RIGHTPADDING",  (0,0),(0,0),   0),
                ("TOPPADDING",    (1,0),(1,0),   6),
                ("BOTTOMPADDING", (1,0),(1,0),   6),
                ("LEFTPADDING",   (1,0),(1,0),   _BL),
                ("RIGHTPADDING",  (1,0),(1,0),   _BR),
                ("LINEBELOW",     (0,0),(-1,-1), 0.5, C["slate_200"]),
            ]))
            story.append(row)
        story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("No insights available.", ps("SNone3", fontSize=8, textColor=C["slate_700"])))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B * 1.4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
    )
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
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

    org_slug   = _get_org_name(location_id)
    timestamp  = datetime.utcnow().strftime("%Y-%m-%d-%H%M")
    type_label = "summary" if (body.format == "pdf" and body.report_type == "summary") else "report"
    filename   = f"truesignal-{org_slug}-{type_label}-{timestamp}.{body.format}"

    try:
        if body.format == "xlsx":
            buf = _generate_xlsx(body.sections, body.days, location_id)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif body.report_type == "summary":
            buf = _generate_summary_pdf(body.sections, body.days, location_id)
            media_type = "application/pdf"
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
