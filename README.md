# 🧾 AI Invoice Processing Agent

> **Drop a PDF invoice → get it extracted, validated, Slack-notified, and logged to QuickBooks — automatically.**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-purple)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST_API-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## The Problem

Finance teams receive dozens of PDF invoices every week. Manually reading, checking math, validating vendor details, and entering data into QuickBooks takes hours — and human error causes duplicate payments, missed discrepancies, and late approvals.

## The Solution

This agent handles the entire AP (Accounts Payable) intake pipeline in seconds:

1. **Extract** — GPT-4o reads the PDF and returns structured JSON (vendor, amount, dates, line items, tax, PO number)
2. **Validate** — business rules check math, dates, required fields, and anomalies
3. **Route** — approved → QuickBooks bill created; flagged/rejected → team alerted
4. **Notify** — Slack message with full invoice summary, issues, and confidence score

---

## Architecture

```
PDF Upload (FastAPI)
        │
        ▼
 ┌─────────────┐
 │  extract    │  GPT-4o structured output → InvoiceData
 └──────┬──────┘
        │
        ▼
 ┌─────────────┐
 │  validate   │  math · dates · required fields · anomaly detection
 └──────┬──────┘
        │
   ┌────┴────┐
   │  route  │  approved / flagged / rejected / error
   └────┬────┘
        │
        ▼
 ┌─────────────┐     ┌──────────────────────┐
 │   notify    │────▶│  Slack Block Kit msg  │
 └──────┬──────┘     └──────────────────────┘
        │
        ▼
 ┌──────────────────┐     ┌───────────────────┐
 │  log_quickbooks  │────▶│  QB Bill (if appr) │
 └──────────────────┘     └───────────────────┘
```

Built with **LangGraph** — each step is an isolated node, easy to swap or extend.

---

## Key Features

| Feature | Detail |
|---|---|
| 🤖 LLM Extraction | GPT-4o with `structured_output` — no regex, no templates |
| ✅ Math Validation | Line items × qty vs total, with $0.05 rounding tolerance |
| 📅 Date Logic | Future dates, due before invoice, invoices >1yr old |
| 🚨 Anomaly Detection | Flags high-value invoices (>$50k) for manager approval |
| 💬 Slack Alerts | Rich Block Kit messages with emoji status and confidence score |
| 📒 QuickBooks | Creates Bills via QBO REST API (OAuth2); stub mode if unconfigured |
| 🐳 Docker | Single `docker compose up` to run |
| 🔌 Modular | Swap any node (e.g. replace QB with NetSuite) without touching others |

---

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/Swty13/ai-automation-agent/invoice-agent.git
cd ai-automation-agent
cp .env.example .env
# → fill in OPENAI_API_KEY (required), SLACK_WEBHOOK_URL (optional)
```

### 2. Run locally

```bash
pip install -r requirements.txt
python main.py
```

### 3. Or with Docker

```bash
docker compose up --build
```

### 4. Upload an invoice

```bash
curl -X POST http://localhost:8000/process \
  -F "file=@invoice.pdf"
```

**Response:**

```json
{
  "invoice": {
    "vendor_name": "Acme Corp",
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-01-15",
    "due_date": "2024-02-15",
    "total_amount": 4250.00,
    "currency": "USD",
    "line_items": []
  },
  "validation": {
    "status": "approved",
    "issues": [],
    "warnings": [],
    "confidence_score": 1.0
  },
  "action": "approved",
  "slack_sent": true,
  "quickbooks_bill_id": "QB-BILL-123"
}
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/process` | POST | Upload PDF → full processing result |
| `/health` | GET | Liveness check |

Swagger docs at `http://localhost:8000/docs` after starting the server.

---

## Validation Rules

The validator runs these checks on every invoice:

- **Required fields** — invoice number, vendor name, total amount
- **Math** — line items sum (+ tax) must match invoice total within $0.05
- **Date logic** — due date must be after invoice date; flags future-dated and >1yr old invoices
- **Amount anomalies** — invoices over $50,000 flagged for manager approval
- **Tax sanity** — tax rates over 40% generate a warning

**Status logic:** `rejected` (2+ issues) → `flagged` (1 issue or any warning) → `approved` (clean)

---

## Project Structure

```
ai-automation-agent/
├── main.py              # FastAPI app (upload endpoint)
├── agent.py             # LangGraph state machine
├── extractor.py         # PDF → InvoiceData (LLM structured output)
├── validator.py         # Business rule validation
├── config.py            # Settings via pydantic-settings
├── integrations/
│   ├── slack.py         # Slack Block Kit notifications
│   └── quickbooks.py    # QuickBooks Online Bill creation
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Extending the Agent

Add a new integration node in 3 steps:

```python
# 1. Write the node function
def log_to_notion_node(state: InvoiceState) -> InvoiceState:
    ...

# 2. Register it
graph.add_node("log_notion", log_to_notion_node)

# 3. Wire it
graph.add_edge("log_quickbooks", "log_notion")
graph.add_edge("log_notion", END)
```

---

## Built For 

This project demonstrates patterns I apply in production AP automation engagements:

- Structured LLM output (no brittle JSON parsing)
- Idempotent nodes for easy retry/replay
- Graceful degradation (runs without QB or Slack configured)
- Docker-first deployment for client handoff

---

