"""
QuickBooks Online integration.
Creates a Bill (AP entry) from extracted invoice data.
Requires OAuth2 setup — see README for instructions.
"""
import requests
from config import settings


BASE_URL = "https://sandbox-quickbooks.api.intuit.com/v3/company"


def get_access_token() -> str:
    """Exchange client credentials for access token. Simplified for demo."""
    # In production: implement full OAuth2 PKCE flow
    # https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization
    raise NotImplementedError(
        "Set up OAuth2 token refresh. See: "
        "https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization"
    )


def create_bill(invoice_data: dict) -> dict | None:
    """
    Create a Bill in QuickBooks from invoice data.
    Returns QB Bill ID on success, None if not configured.
    """
    if not settings.quickbooks_client_id:
        print(f"[QB] Would create bill: {invoice_data.get('vendor_name')} — ${invoice_data.get('total_amount')}")
        return {"id": "STUB-QB-BILL", "status": "simulated"}

    try:
        token = get_access_token()
    except NotImplementedError:
        print("[QB] QuickBooks not configured. Skipping bill creation.")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Map extracted invoice → QB Bill format
    line_items = [
        {
            "Amount": item.get("total", 0),
            "DetailType": "AccountBasedExpenseLineDetail",
            "AccountBasedExpenseLineDetail": {
                "AccountRef": {"value": "1"},  # replace with your expense account ID
                "BillableStatus": "NotBillable",
            },
            "Description": item.get("description", ""),
        }
        for item in invoice_data.get("line_items", [])
    ] or [
        {
            "Amount": invoice_data.get("total_amount", 0),
            "DetailType": "AccountBasedExpenseLineDetail",
            "AccountBasedExpenseLineDetail": {
                "AccountRef": {"value": "1"},
            },
            "Description": "Invoice total",
        }
    ]

    bill_payload = {
        "VendorRef": {"name": invoice_data.get("vendor_name", "Unknown Vendor")},
        "TxnDate": invoice_data.get("invoice_date"),
        "DueDate": invoice_data.get("due_date"),
        "DocNumber": invoice_data.get("invoice_number"),
        "Line": line_items,
        "TotalAmt": invoice_data.get("total_amount", 0),
        "CurrencyRef": {"value": invoice_data.get("currency", "USD")},
    }

    url = f"{BASE_URL}/{settings.quickbooks_realm_id}/bill"
    resp = requests.post(url, headers=headers, json={"Bill": bill_payload}, timeout=10)
    resp.raise_for_status()
    return resp.json().get("Bill", {})
