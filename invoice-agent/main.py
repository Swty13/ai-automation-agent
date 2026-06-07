"""
FastAPI entry point for the Invoice Processing Agent.

Endpoints:
  POST /process  — Upload a PDF invoice, get back structured result
  GET  /health   — Liveness check
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from agent import process_invoice

app = FastAPI(
    title="AI Invoice Processing Agent",
    description=(
        "Automatically extracts, validates, and routes invoices from PDF. "
        "Sends Slack alerts and creates QuickBooks bills on approval."
    ),
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process")
async def process(file: UploadFile = File(...)):
    """
    Upload a PDF invoice.

    Returns:
    - invoice: extracted fields (vendor, amount, dates, line items …)
    - validation: status (approved | flagged | rejected), issues, warnings, confidence
    - action: final routing decision
    - slack_sent: whether Slack notification was delivered
    - quickbooks_bill_id: QB bill ID if created, else empty string
    - error: non-empty if extraction or processing failed
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    result = process_invoice(pdf_bytes)

    # Surface errors as 422 so clients can distinguish processing failures
    if result.get("error"):
        return JSONResponse(status_code=422, content=result)

    return result


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
