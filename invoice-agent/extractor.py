"""
Invoice field extractor.
Uses LLM to pull structured data from raw PDF text.
Handles messy real-world invoices — different layouts, currencies, date formats.
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from pydantic import BaseModel, Field
from typing import Optional
from config import settings
import tempfile, os

llm = ChatOpenAI(model=settings.llm_model, temperature=0)

EXTRACTION_PROMPT = """You are an expert invoice parser. Extract all fields from the invoice text below.
Return ONLY valid JSON. If a field is missing, use null.

Invoice text:
{text}

Return JSON with exactly these fields:
{{
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "vendor_name": "string or null",
  "vendor_email": "string or null",
  "vendor_address": "string or null",
  "bill_to": "string or null",
  "line_items": [
    {{"description": "string", "quantity": number, "unit_price": number, "total": number}}
  ],
  "subtotal": number or null,
  "tax_amount": number or null,
  "tax_rate_percent": number or null,
  "total_amount": number or null,
  "currency": "USD/EUR/GBP/etc or null",
  "payment_terms": "string or null",
  "purchase_order_number": "string or null",
  "notes": "string or null"
}}"""


class InvoiceData(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_email: Optional[str] = None
    vendor_address: Optional[str] = None
    bill_to: Optional[str] = None
    line_items: list[dict] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    tax_rate_percent: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = "USD"
    payment_terms: Optional[str] = None
    purchase_order_number: Optional[str] = None
    notes: Optional[str] = None


def extract_from_pdf(pdf_path: str) -> InvoiceData:
    """Load PDF, extract text, parse fields with LLM."""
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    full_text = "\n".join(p.page_content for p in pages)

    prompt = PromptTemplate(
        template=EXTRACTION_PROMPT,
        input_variables=["text"]
    )

    structured_llm = llm.with_structured_output(InvoiceData)
    result = structured_llm.invoke(prompt.format(text=full_text[:6000]))  # cap tokens
    return result


def extract_from_bytes(pdf_bytes: bytes) -> InvoiceData:
    """Extract from raw PDF bytes (for API upload)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        return extract_from_pdf(tmp_path)
    finally:
        os.unlink(tmp_path)
