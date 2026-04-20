"""
Email service using Resend.

All outbound emails go through this module.
Set RESEND_API_KEY and EMAIL_FROM in .env.
"""

import os
import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.environ.get("RESEND_API_KEY", "")
FROM_ADDRESS = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
APP_NAME = "TrueSignal"
APP_URL = os.environ.get("APP_URL", "http://localhost:5173")


def _send(to: str, subject: str, html: str) -> bool:
    """Send an email. Returns True on success, False on failure."""
    if not resend.api_key:
        print(f"[email] RESEND_API_KEY not set — skipping email to {to}")
        return False
    try:
        resend.Emails.send({
            "from": f"{APP_NAME} <{FROM_ADDRESS}>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        print(f"[email] Failed to send to {to}: {e}")
        return False


# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

def _base_template(content: str) -> str:
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: #0f172a; color: #e2e8f0; max-width: 560px;
                margin: 0 auto; padding: 32px 24px; border-radius: 12px;">
      <div style="margin-bottom: 28px;">
        <span style="font-size: 20px; font-weight: 700; color: #fff;">True</span>
        <span style="font-size: 20px; font-weight: 700; color: #34d399;">Signal</span>
        <p style="font-size: 10px; color: #6366f1; letter-spacing: 0.15em;
                  text-transform: uppercase; margin: 2px 0 0;">Maintenance Intelligence</p>
      </div>
      {content}
      <div style="margin-top: 32px; padding-top: 20px; border-top: 1px solid #1e293b;
                  font-size: 11px; color: #475569; text-align: center;">
        TrueSignal · Predictive Maintenance Intelligence<br>
        <a href="{APP_URL}" style="color: #6366f1; text-decoration: none;">{APP_URL}</a>
      </div>
    </div>
    """


def send_verification_email(to: str, name: str, token: str) -> bool:
    verify_url = f"{APP_URL}/verify-email?token={token}"
    content = f"""
      <h2 style="color: #fff; font-size: 22px; margin: 0 0 8px;">Verify your email</h2>
      <p style="color: #94a3b8; margin: 0 0 24px;">
        Hi {name}, welcome to TrueSignal. Click the button below to verify your email address and activate your account.
      </p>
      <a href="{verify_url}"
         style="display: inline-block; background: #6366f1; color: #fff;
                font-weight: 600; font-size: 14px; padding: 12px 28px;
                border-radius: 8px; text-decoration: none; margin-bottom: 24px;">
        Verify Email Address
      </a>
      <p style="color: #475569; font-size: 12px; margin: 0;">
        This link expires in 24 hours. If you didn't create a TrueSignal account, you can safely ignore this email.
      </p>
    """
    return _send(to, "Verify your TrueSignal email", _base_template(content))


def send_alert_email(to: str, name: str, alerts: list[dict]) -> bool:
    """
    Send an alert digest email.
    alerts: list of {"title": str, "description": str, "severity": "critical"|"high"|"medium"}
    """
    severity_colors = {
        "critical": "#f87171",
        "high":     "#fb923c",
        "medium":   "#fbbf24",
    }

    alert_rows = ""
    for alert in alerts:
        color = severity_colors.get(alert.get("severity", "medium"), "#94a3b8")
        alert_rows += f"""
          <div style="border-left: 3px solid {color}; padding: 10px 14px;
                      background: #1e293b; border-radius: 0 6px 6px 0; margin-bottom: 10px;">
            <p style="margin: 0 0 4px; font-weight: 600; color: #fff; font-size: 13px;">
              {alert['title']}
            </p>
            <p style="margin: 0; color: #94a3b8; font-size: 12px;">{alert['description']}</p>
          </div>
        """

    content = f"""
      <h2 style="color: #fff; font-size: 22px; margin: 0 0 8px;">Maintenance Alert</h2>
      <p style="color: #94a3b8; margin: 0 0 20px;">
        Hi {name}, the following conditions were detected in your latest sync:
      </p>
      {alert_rows}
      <a href="{APP_URL}/dashboard/"
         style="display: inline-block; background: #1e293b; color: #6366f1;
                font-weight: 600; font-size: 13px; padding: 10px 24px;
                border-radius: 8px; text-decoration: none; border: 1px solid #334155;
                margin-top: 8px;">
        View Dashboard
      </a>
    """
    return _send(to, f"TrueSignal Alert — {len(alerts)} condition{'s' if len(alerts) != 1 else ''} detected", _base_template(content))


def send_password_reset_email(to: str, name: str, token: str) -> bool:
    reset_url = f"{APP_URL}/reset-password?token={token}"
    content = f"""
      <h2 style="color: #fff; font-size: 22px; margin: 0 0 8px;">Reset your password</h2>
      <p style="color: #94a3b8; margin: 0 0 24px;">
        Hi {name}, we received a request to reset your TrueSignal password.
        Click the button below to choose a new password. This link expires in 1 hour.
      </p>
      <a href="{reset_url}"
         style="display: inline-block; background: #6366f1; color: #fff;
                font-weight: 600; font-size: 14px; padding: 12px 28px;
                border-radius: 8px; text-decoration: none; margin-bottom: 24px;">
        Reset Password
      </a>
      <p style="color: #475569; font-size: 12px; margin: 0;">
        If you didn't request a password reset, you can safely ignore this email.
        Your password will not change.
      </p>
    """
    return _send(to, "Reset your TrueSignal password", _base_template(content))


def send_welcome_email(to: str, name: str) -> bool:
    content = f"""
      <h2 style="color: #fff; font-size: 22px; margin: 0 0 8px;">You're in.</h2>
      <p style="color: #94a3b8; margin: 0 0 20px;">
        Hi {name}, your TrueSignal account is active. Connect your CMMS in Settings to start
        seeing predictive insights for your facility.
      </p>
      <a href="{APP_URL}/dashboard/settings"
         style="display: inline-block; background: #6366f1; color: #fff;
                font-weight: 600; font-size: 14px; padding: 12px 28px;
                border-radius: 8px; text-decoration: none;">
        Go to Settings
      </a>
    """
    return _send(to, f"Welcome to {APP_NAME}", _base_template(content))
