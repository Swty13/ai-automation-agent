"""
LangGraph Invoice Processing Agent.

State machine:
  extract → validate → route → [notify + log] → done

Each node is a pure function: takes state, returns updated state.
Swap any node without touching the others.
"""
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from extractor import InvoiceData, extract_from_bytes
from validator import validate, ValidationResult
from integrations.slack import send_invoice_alert
from integrations.quickbooks import create_bill
import json


# ─── State ────────────────────────────────────────────────────────────────────

class InvoiceState(TypedDict):
    pdf_bytes: bytes
    invoice: dict           # InvoiceData as dict
    validation: dict        # ValidationResult as dict
    action: str             # approved | flagged | rejected
    slack_sent: bool
    quickbooks_bill_id: str
    error: str


# ─── Nodes ────────────────────────────────────────────────────────────────────

def extract_node(state: InvoiceState) -> InvoiceState:
    """Parse PDF and extract structured invoice fields."""
    try:
        invoice: InvoiceData = extract_from_bytes(state["pdf_bytes"])
        return {**state, "invoice": invoice.model_dump(), "error": ""}
    except Exception as e:
        return {**state, "error": f"Extraction failed: {e}"}


def validate_node(state: InvoiceState) -> InvoiceState:
    """Run validation checks on extracted data."""
    if state.get("error"):
        return state

    from extractor import InvoiceData
    invoice = InvoiceData(**state["invoice"])
    result: ValidationResult = validate(invoice)

    return {
        **state,
        "validation": {
            "status": result.status,
            "issues": result.issues,
            "warnings": result.warnings,
            "confidence_score": result.confidence_score,
        },
        "action": result.status,
    }


def notify_node(state: InvoiceState) -> InvoiceState:
    """Send Slack alert regardless of outcome."""
    if state.get("error"):
        return state

    sent = send_invoice_alert(state["invoice"], state["validation"])
    return {**state, "slack_sent": sent}


def log_to_quickbooks_node(state: InvoiceState) -> InvoiceState:
    """Only create QB bill if invoice is approved."""
    if state.get("error") or state["action"] != "approved":
        return {**state, "quickbooks_bill_id": ""}

    result = create_bill(state["invoice"])
    bill_id = result.get("id", "") if result else ""
    return {**state, "quickbooks_bill_id": bill_id}


# ─── Routing ──────────────────────────────────────────────────────────────────

def route_after_validate(state: InvoiceState) -> Literal["notify", "end_error"]:
    if state.get("error"):
        return "end_error"
    return "notify"


# ─── Graph ────────────────────────────────────────────────────────────────────

def build_agent():
    graph = StateGraph(InvoiceState)

    graph.add_node("extract", extract_node)
    graph.add_node("validate", validate_node)
    graph.add_node("notify", notify_node)
    graph.add_node("log_quickbooks", log_to_quickbooks_node)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {"notify": "notify", "end_error": END}
    )
    graph.add_edge("notify", "log_quickbooks")
    graph.add_edge("log_quickbooks", END)

    return graph.compile()


agent = build_agent()


def process_invoice(pdf_bytes: bytes) -> dict:
    """Main entry point. Pass PDF bytes, get full result back."""
    initial_state: InvoiceState = {
        "pdf_bytes": pdf_bytes,
        "invoice": {},
        "validation": {},
        "action": "",
        "slack_sent": False,
        "quickbooks_bill_id": "",
        "error": "",
    }
    result = agent.invoke(initial_state)
    # Don't return raw bytes in response
    result.pop("pdf_bytes", None)
    return result
