"""
Support message endpoint — POST /support/message
Sends user message to support@truesignalapp.com via Resend.
No auth required so unauthenticated users can also reach support.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from .email_service import _send, _base_template

router = APIRouter(prefix="/support", tags=["Support"])

SUPPORT_INBOX = "support@truesignalapp.com"


class SupportMessage(BaseModel):
    name: str = ""
    email: str = ""
    subject: str = "Support request"
    message: str


@router.post("/message")
def send_support_message(body: SupportMessage):
    if not body.message.strip():
        return {"sent": False, "error": "Message cannot be empty"}

    sender_label = body.name.strip() or "Anonymous"
    reply_from = body.email.strip() or "no-reply"

    html = _base_template(f"""
      <h2 style="color:#fff;font-size:20px;margin:0 0 8px;">Support Request</h2>
      <p style="color:#94a3b8;margin:0 0 20px;font-size:13px;">
        A new support message was submitted via TrueSignal.
      </p>
      <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
        <tr>
          <td style="color:#64748b;font-size:12px;padding:6px 0;width:80px;">From</td>
          <td style="color:#e2e8f0;font-size:13px;padding:6px 0;">{sender_label}</td>
        </tr>
        <tr>
          <td style="color:#64748b;font-size:12px;padding:6px 0;">Email</td>
          <td style="color:#e2e8f0;font-size:13px;padding:6px 0;">{reply_from}</td>
        </tr>
        <tr>
          <td style="color:#64748b;font-size:12px;padding:6px 0;">Subject</td>
          <td style="color:#e2e8f0;font-size:13px;padding:6px 0;">{body.subject}</td>
        </tr>
      </table>
      <div style="background:#1e293b;border-radius:8px;padding:16px;border-left:3px solid #6366f1;">
        <p style="color:#e2e8f0;font-size:13px;margin:0;white-space:pre-wrap;line-height:1.6;">
          {body.message.strip()}
        </p>
      </div>
    """)

    sent = _send(SUPPORT_INBOX, f"[TrueSignal Support] {body.subject}", html)
    return {"sent": sent}
