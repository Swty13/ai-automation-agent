"""
Invoice validator.
Checks extracted fields for common errors, flags anomalies,
and produces a structured validation report.
"""
from extractor import InvoiceData
from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime


@dataclass
class ValidationResult:
    status: Literal["approved", "flagged", "rejected"]
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence_score: float = 1.0  # 0.0 – 1.0


def validate(invoice: InvoiceData) -> ValidationResult:
    """Run all validation checks. Returns structured result."""
    issues = []
    warnings = []

    # ── Required fields ──────────────────────────────────────────────
    if not invoice.invoice_number:
        issues.append("Missing invoice number")
    if not invoice.vendor_name:
        issues.append("Missing vendor name")
    if not invoice.total_amount:
        issues.append("Missing total amount")
    if not invoice.invoice_date:
        warnings.append("Invoice date not found")

    # ── Math validation ───────────────────────────────────────────────
    if invoice.line_items and invoice.total_amount:
        computed_subtotal = sum(
            item.get("total", item.get("quantity", 0) * item.get("unit_price", 0))
            for item in invoice.line_items
        )
        expected_total = computed_subtotal + (invoice.tax_amount or 0)
        diff = abs(expected_total - invoice.total_amount)
        if diff > 0.05:  # allow $0.05 rounding tolerance
            issues.append(
                f"Total mismatch: line items sum to {expected_total:.2f} "
                f"but invoice total is {invoice.total_amount:.2f}"
            )

    # ── Amount anomaly detection ──────────────────────────────────────
    if invoice.total_amount:
        if invoice.total_amount > 50_000:
            warnings.append(f"High-value invoice: {invoice.currency} {invoice.total_amount:,.2f} — requires manager approval")
        if invoice.total_amount <= 0:
            issues.append("Total amount must be greater than 0")

    # ── Date validation ───────────────────────────────────────────────
    if invoice.invoice_date:
        try:
            inv_date = datetime.strptime(invoice.invoice_date, "%Y-%m-%d")
            if inv_date > datetime.now():
                warnings.append("Invoice date is in the future")
            if (datetime.now() - inv_date).days > 365:
                warnings.append("Invoice is over 1 year old")
        except ValueError:
            warnings.append(f"Could not parse invoice date: {invoice.invoice_date}")

    if invoice.due_date and invoice.invoice_date:
        try:
            due = datetime.strptime(invoice.due_date, "%Y-%m-%d")
            inv = datetime.strptime(invoice.invoice_date, "%Y-%m-%d")
            if due < inv:
                issues.append("Due date is before invoice date")
        except ValueError:
            pass

    # ── Tax sanity check ──────────────────────────────────────────────
    if invoice.tax_rate_percent and invoice.tax_rate_percent > 40:
        warnings.append(f"Unusually high tax rate: {invoice.tax_rate_percent}%")

    # ── Determine status ─────────────────────────────────────────────
    confidence = max(0.0, 1.0 - (len(issues) * 0.3) - (len(warnings) * 0.1))

    if issues:
        status = "rejected" if len(issues) >= 2 else "flagged"
    elif warnings:
        status = "flagged"
    else:
        status = "approved"

    return ValidationResult(
        status=status,
        issues=issues,
        warnings=warnings,
        confidence_score=round(confidence, 2),
    )
