"""
Slack integration — sends invoice processing results to a channel.
"""
import requests
from config import settings


def send_invoice_alert(invoice_data: dict, validation: dict) -> bool:
    """Post invoice result to Slack. Returns True if sent successfully."""
    if not settings.slack_webhook_url:
        print(f"[SLACK] {invoice_data.get('vendor_name')} | {validation.get('status')} | ${invoice_data.get('total_amount')}")
        return False

    status = validation.get("status", "unknown")
    emoji = {"approved": "✅", "flagged": "⚠️", "rejected": "❌"}.get(status, "📄")

    issues_text = "\n".join(f"• {i}" for i in validation.get("issues", [])) or "None"
    warnings_text = "\n".join(f"• {w}" for w in validation.get("warnings", [])) or "None"

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} Invoice {status.upper()}: {invoice_data.get('vendor_name', 'Unknown Vendor')}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Invoice #*\n{invoice_data.get('invoice_number', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Amount*\n{invoice_data.get('currency', 'USD')} {invoice_data.get('total_amount', 0):,.2f}"},
                    {"type": "mrkdwn", "text": f"*Date*\n{invoice_data.get('invoice_date', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Due*\n{invoice_data.get('due_date', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Confidence*\n{validation.get('confidence_score', 0) * 100:.0f}%"},
                    {"type": "mrkdwn", "text": f"*PO Number*\n{invoice_data.get('purchase_order_number', 'N/A')}"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Issues:*\n{issues_text}\n\n*Warnings:*\n{warnings_text}"}
            }
        ]
    }

    resp = requests.post(settings.slack_webhook_url, json=message, timeout=5)
    return resp.status_code == 200
