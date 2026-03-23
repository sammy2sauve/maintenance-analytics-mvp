"""
Report generation endpoints -- POST /reports/generate

Supports CSV and PDF export of:
- Overview Summary (asset counts, risk distribution, savings)
- Asset Health Breakdown (all assets)
- Critical & High Risk Assets (filtered)
- PM Recommendations
- AI Insights
"""

import io
import csv
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


def _current_location(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    user_id = int(payload["sub"])
    locs = get_user_locations(user_id)
    if not locs:
        raise HTTPException(400, "No locations found for this user")
    return locs[0]["id"]


class ReportRequest(BaseModel):
    sections: List[str]
    days: Optional[int] = None   # None = all time
    format: str = "csv"          # "csv" or "pdf"


SECTION_LABELS = {
    "overview":       "Overview Summary",
    "asset_health":   "Asset Health Breakdown",
    "critical_assets": "Critical & High Risk Assets",
    "pm_suggestions": "PM Recommendations",
    "insights":       "AI Insights",
}

RISK_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _clean(val):
    if isinstance(val, float) and not math.isfinite(val):
        return None
    return val


def _apply_date_filter(df, date_col: str, days: Optional[int]):
    """Filter a DataFrame to rows within the last `days` days."""
    if days and date_col in df.columns:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = df[df[date_col] >= cutoff]
    return df


def _dedup_predictions(df):
    """Keep only the latest prediction per asset (same logic as api_predictions.py)."""
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
        records = (
            sorted(
                [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")],
                key=lambda r: RISK_ORDER.get(r.get("risk_level", "LOW"), 99),
            )
            if not df.empty else []
        )
        data["_predictions"] = records

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
            # Deduplicate by title (known DB issue)
            df = df.drop_duplicates(subset="title", keep="first")
        data["insights"] = (
            [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]
            if not df.empty else []
        )

    return data


def _overview_stats(data: dict, location_id: int):
    """Compute summary stats shared between CSV and PDF."""
    preds = data.get("_predictions", [])
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for p in preds:
        rl = p.get("risk_level", "LOW")
        counts[rl] = counts.get(rl, 0) + 1
    scores = [p["failure_probability"] for p in preds if p.get("failure_probability") is not None]
    avg_score = round(sum(scores) / len(scores), 3) if scores else None

    pm_df = retrieve_pm_optimization_suggestions(status="pending", limit=10000, location_id=location_id)
    savings = round(float(pm_df["estimated_cost_savings"].sum()), 2) if not pm_df.empty else 0.0

    return preds, counts, avg_score, savings


# ── CSV ───────────────────────────────────────────────────────────────────────

def _fmt_prob(val) -> str:
    """Format failure probability as percentage string."""
    if val is None:
        return "—"
    return f"{float(val) * 100:.1f}%"


def _fmt_days(val) -> str:
    if val is None:
        return "—"
    return str(int(val))


def _fmt_savings(val) -> str:
    if val is None:
        return "$0"
    return f"${float(val):,.0f}"


def _generate_csv(sections: List[str], days: Optional[int], location_id: int) -> io.BytesIO:
    data = _fetch_data(sections, days, location_id)
    buf = io.StringIO()
    w = csv.writer(buf)

    period_label = f"Last {days} days" if days else "All time"
    gen_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # ── File header ────────────────────────────────────────────────────────────
    w.writerow(["TrueSignal Maintenance Intelligence Report"])
    w.writerow(["Generated", gen_time])
    w.writerow(["Period", period_label])
    w.writerow([])

    for section in sections:
        label = SECTION_LABELS.get(section, section)
        # Section divider
        w.writerow([f"--- {label.upper()} ---"])

        if section == "overview":
            preds, counts, avg_score, savings = _overview_stats(data, location_id)
            w.writerow(["Metric", "Value", "Note"])
            w.writerow(["Total Assets Monitored", len(preds), ""])
            w.writerow(["Critical Risk Assets", counts["CRITICAL"], "Immediate action required"])
            w.writerow(["High Risk Assets",     counts["HIGH"],     "Schedule within 30 days"])
            w.writerow(["Medium Risk Assets",   counts["MEDIUM"],   "Monitor closely"])
            w.writerow(["Low Risk Assets",      counts["LOW"],      "On track"])
            w.writerow(["Avg Failure Probability",
                        f"{avg_score * 100:.1f}%" if avg_score is not None else "—", ""])
            w.writerow(["Total Savings Potential", _fmt_savings(savings), "Pending PM recommendations"])
            w.writerow([])

        elif section in ("asset_health", "critical_assets"):
            preds = data.get("_predictions", [])
            if section == "critical_assets":
                preds = [p for p in preds if p.get("risk_level") in ("CRITICAL", "HIGH")]
            if preds:
                w.writerow(["Asset ID", "Risk Level", "Failure Probability",
                            "Days to Failure", "Days Since Last PM",
                            "Reactive WOs (90d)", "Recommendation"])
                for p in preds:
                    w.writerow([
                        p.get("asset_id", ""),
                        p.get("risk_level", ""),
                        _fmt_prob(p.get("failure_probability")),
                        _fmt_days(p.get("days_to_predicted_failure")),
                        _fmt_days(p.get("days_since_last_pm")),
                        p.get("reactive_work_count_90d") or 0,
                        p.get("recommendation", ""),
                    ])
            else:
                w.writerow(["No data available for this period."])
            w.writerow([])

        elif section == "pm_suggestions":
            pms = data.get("pm_suggestions", [])
            if pms:
                w.writerow(["Asset ID", "Current PM Interval", "Suggested PM Interval",
                            "Est. Annual Savings", "Status", "Reason"])
                for p in pms:
                    curr = p.get("current_pm_frequency_days")
                    sugg = p.get("suggested_pm_frequency_days")
                    w.writerow([
                        p.get("asset_id", ""),
                        f"{curr} days" if curr else "—",
                        f"{sugg} days" if sugg else "—",
                        _fmt_savings(p.get("estimated_cost_savings")),
                        (p.get("status") or "pending").title(),
                        p.get("reason", ""),
                    ])
            else:
                w.writerow(["No PM recommendations available."])
            w.writerow([])

        elif section == "insights":
            ins = data.get("insights", [])
            if ins:
                w.writerow(["Type", "Title", "Description", "Impact Level", "Affected Assets", "Date"])
                for i in ins:
                    insight_type = (i.get("insight_type") or "").replace("_", " ").title()
                    w.writerow([
                        insight_type,
                        i.get("title", ""),
                        i.get("description", ""),
                        (i.get("impact_level") or "").title(),
                        i.get("affected_assets", ""),
                        (i.get("insight_date") or "")[:10],
                    ])
            else:
                w.writerow(["No insights available."])
            w.writerow([])

    w.writerow(["Generated by TrueSignal Maintenance Intelligence"])

    # utf-8-sig BOM makes Excel open CSV without encoding issues
    return io.BytesIO(buf.getvalue().encode("utf-8-sig"))


# ── PDF ───────────────────────────────────────────────────────────────────────

def _generate_pdf(sections: List[str], days: Optional[int], location_id: int) -> io.BytesIO:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER

    INDIGO    = colors.HexColor("#6366f1")
    SLATE_900 = colors.HexColor("#0f172a")
    SLATE_700 = colors.HexColor("#334155")
    SLATE_400 = colors.HexColor("#94a3b8")
    LIGHT_BG  = colors.HexColor("#f8fafc")
    BORDER    = colors.HexColor("#e2e8f0")
    RED       = colors.HexColor("#ef4444")
    ORANGE    = colors.HexColor("#f97316")
    AMBER     = colors.HexColor("#f59e0b")
    GREEN     = colors.HexColor("#10b981")
    WHITE     = colors.white

    RISK_FG = {"CRITICAL": RED, "HIGH": ORANGE, "MEDIUM": AMBER, "LOW": GREEN}
    IMPACT_FG = {"High": RED, "Medium": AMBER, "Low": GREEN}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()

    def style(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    title_sty    = style("T", fontSize=20, textColor=SLATE_900, fontName="Helvetica-Bold", spaceAfter=2)
    sub_sty      = style("S", fontSize=10, textColor=INDIGO, spaceAfter=4)
    meta_sty     = style("M", fontSize=8,  textColor=SLATE_400, spaceAfter=0)
    section_sty  = style("Se", fontSize=13, textColor=SLATE_900, fontName="Helvetica-Bold",
                         spaceBefore=16, spaceAfter=8)
    body_sty     = style("B", fontSize=9,  textColor=SLATE_700, leading=14)
    footer_sty   = style("F", fontSize=7,  textColor=SLATE_400, alignment=TA_CENTER)

    BASE_TABLE = [
        ("BACKGROUND",   (0, 0), (-1, 0),  INDIGO),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("FONTSIZE",     (0, 1), (-1, -1), 8),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("GRID",         (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]

    def make_table(rows, col_widths, extra_styles=None):
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        ts = TableStyle(BASE_TABLE[:])
        for cmd in (extra_styles or []):
            ts.add(*cmd)
        t.setStyle(ts)
        return t

    story = []
    period_label = f"Last {days} days" if days else "All time"
    gen_time = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

    story.append(Paragraph("TrueSignal", title_sty))
    story.append(Paragraph("Maintenance Intelligence Report", sub_sty))
    story.append(HRFlowable(width="100%", thickness=1, color=INDIGO, spaceAfter=6))
    story.append(Paragraph(f"Generated {gen_time}  ·  Period: {period_label}", meta_sty))
    story.append(Spacer(1, 0.2 * inch))

    data = _fetch_data(sections, days, location_id)

    for section in sections:
        label = SECTION_LABELS.get(section, section)
        story.append(Paragraph(label, section_sty))

        if section == "overview":
            preds, counts, avg_score, savings = _overview_stats(data, location_id)
            rows = [
                ["Metric", "Value"],
                ["Total Assets Monitored", str(len(preds))],
                ["Critical Risk", str(counts["CRITICAL"])],
                ["High Risk",     str(counts["HIGH"])],
                ["Medium Risk",   str(counts["MEDIUM"])],
                ["Low Risk (Safe)", str(counts["LOW"])],
                ["Avg Failure Probability", f"{avg_score:.3f}" if avg_score is not None else "—"],
                ["Savings Potential", f"${savings:,.2f}"],
            ]
            extra = [
                ("TEXTCOLOR", (1, 2), (1, 2), RED),
                ("TEXTCOLOR", (1, 3), (1, 3), ORANGE),
                ("TEXTCOLOR", (1, 4), (1, 4), AMBER),
                ("TEXTCOLOR", (1, 5), (1, 5), GREEN),
                ("FONTNAME",  (1, 2), (1, 5), "Helvetica-Bold"),
                ("TEXTCOLOR", (1, 7), (1, 7), colors.HexColor("#10b981")),
                ("FONTNAME",  (1, 7), (1, 7), "Helvetica-Bold"),
            ]
            story.append(make_table(rows, [3.5 * inch, 2.5 * inch], extra))

        elif section in ("asset_health", "critical_assets"):
            preds = data.get("_predictions", [])
            if section == "critical_assets":
                preds = [p for p in preds if p.get("risk_level") in ("CRITICAL", "HIGH")]
            if preds:
                rows = [["Asset ID", "Risk", "Fail Prob", "Days to Fail", "Days Since PM", "Reactive WOs"]]
                extra = []
                for ri, p in enumerate(preds, start=1):
                    fp = p.get("failure_probability")
                    rows.append([
                        p.get("asset_id", ""),
                        p.get("risk_level", ""),
                        f"{fp:.3f}" if fp is not None else "—",
                        str(p.get("days_to_predicted_failure") or "—"),
                        str(p.get("days_since_last_pm") or "—"),
                        str(p.get("reactive_work_count_90d") or "0"),
                    ])
                    fc = RISK_FG.get(p.get("risk_level", "LOW"), SLATE_700)
                    extra += [
                        ("TEXTCOLOR", (1, ri), (1, ri), fc),
                        ("FONTNAME",  (1, ri), (1, ri), "Helvetica-Bold"),
                    ]
                col_w = [1.4*inch, 0.8*inch, 0.8*inch, 0.85*inch, 1.0*inch, 0.85*inch]
                story.append(make_table(rows, col_w, extra))
            else:
                story.append(Paragraph("No assets found for this period.", body_sty))

        elif section == "pm_suggestions":
            pms = data.get("pm_suggestions", [])
            if pms:
                rows = [["Asset ID", "Current PM", "Suggested PM", "Est. Savings", "Status"]]
                for p in pms:
                    rows.append([
                        p.get("asset_id", ""),
                        f"{p.get('current_pm_frequency_days', '—')}d",
                        f"{p.get('suggested_pm_frequency_days', '—')}d",
                        f"${p.get('estimated_cost_savings', 0) or 0:,.0f}",
                        (p.get("status") or "pending").title(),
                    ])
                col_w = [1.5*inch, 1.0*inch, 1.1*inch, 1.0*inch, 1.0*inch]
                story.append(make_table(rows, col_w))
            else:
                story.append(Paragraph("No PM recommendations available.", body_sty))

        elif section == "insights":
            ins = data.get("insights", [])
            if ins:
                rows = [["Type", "Title", "Impact", "Date"]]
                extra = []
                for ri, i in enumerate(ins, start=1):
                    impact = (i.get("impact_level") or "").title()
                    rows.append([
                        (i.get("insight_type") or "").replace("_", " ").title(),
                        i.get("title", ""),
                        impact,
                        (i.get("insight_date") or "")[:10],
                    ])
                    fc = IMPACT_FG.get(impact, SLATE_700)
                    extra += [
                        ("TEXTCOLOR", (2, ri), (2, ri), fc),
                        ("FONTNAME",  (2, ri), (2, ri), "Helvetica-Bold"),
                    ]
                col_w = [1.0*inch, 3.2*inch, 0.75*inch, 0.75*inch]
                story.append(make_table(rows, col_w, extra))
            else:
                story.append(Paragraph("No insights available.", body_sty))

        story.append(Spacer(1, 0.15 * inch))

    story.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_400, spaceBefore=12))
    story.append(Paragraph(
        "Generated by TrueSignal Maintenance Intelligence",
        footer_sty,
    ))

    doc.build(story)
    buf.seek(0)
    return buf


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/generate")
def generate_report(
    body: ReportRequest,
    location_id: int = Depends(_current_location),
):
    if not body.sections:
        raise HTTPException(400, "At least one section must be selected")
    if body.format not in ("csv", "pdf"):
        raise HTTPException(400, "Format must be 'csv' or 'pdf'")

    date_str = datetime.utcnow().strftime("%Y%m%d")
    filename = f"truesignal-report-{date_str}.{body.format}"

    try:
        if body.format == "csv":
            buf = _generate_csv(body.sections, body.days, location_id)
            media_type = "text/csv"
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
