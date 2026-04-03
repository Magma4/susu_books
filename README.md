# 📒 Susu Books

**Offline, voice-first AI business copilot for informal economy workers.**

Street vendors, market women, and smallholder farmers can speak naturally about their business transactions — purchases, sales, expenses — and Susu Books extracts structured data, maintains a ledger, tracks inventory, and provides business intelligence. Everything runs **locally**. No cloud required.

Built for the **Gemma 4 Good Hackathon on Kaggle** (deadline: May 18, 2026).

---

## Architecture

```
susu-books/
├── backend/          ← FastAPI + SQLite + Gemma 4 via Ollama
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── ai.py           ← /api/chat, /api/chat/image, /api/health
│   │   ├── transactions.py ← /api/transactions CRUD
│   │   ├── inventory.py    ← /api/inventory
│   │   └── reports.py      ← /api/summary/daily, /api/summary/weekly, /api/export/credit-profile
│   └── services/
│       ├── gemma_service.py     ← Ollama function-calling loop
│       ├── ledger_service.py    ← Purchase / sale / expense recording
│       ├── inventory_service.py ← Weighted-average-cost stock management
│       └── report_service.py   ← Daily / weekly / credit-profile reports
└── frontend/         ← Next.js 14 (Phase 2)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14+ (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.11+) |
| AI Model | Gemma 4 (31B or 26B MoE) via Ollama |
| Database | SQLite + SQLAlchemy (async) |
| Voice Input | Browser Web Speech API |
| Voice Output | Browser SpeechSynthesis API |
| Vision/OCR | Gemma 4 multimodal (base64 image input) |

## Prerequisites

1. **Python 3.11+**
2. **Ollama** installed and running: https://ollama.ai
3. Pull the Gemma 4 model:
   ```bash
   ollama pull gemma4:31b-instruct
   # or the lighter MoE variant:
   ollama pull gemma4:26b-a4b-instruct
   ```

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Main voice/text → Gemma function-calling loop |
| `POST` | `/api/chat/image` | Receipt / handwritten note OCR |
| `GET` | `/api/health` | Ollama + DB connectivity check |
| `GET` | `/api/transactions` | List transactions (filterable by date/type) |
| `GET` | `/api/inventory` | Current stock levels + low-stock alerts |
| `GET` | `/api/summary/daily` | Daily P&L summary |
| `GET` | `/api/summary/weekly` | 7-day rolling report |
| `GET` | `/api/export/credit-profile` | Creditworthiness data export |

## Gemma 4 Function Calling

When a user says *"I bought 3 bags of rice for 150 cedis each from Kofi"*, Gemma generates:

```json
{
  "name": "record_purchase",
  "parameters": {
    "item": "rice",
    "quantity": 3,
    "unit_price": 150,
    "unit": "bags",
    "supplier": "Kofi",
    "currency": "GHS"
  }
}
```

The backend executes this against SQLite and feeds the result back to Gemma, which then confirms in the user's language (English, Twi, Hausa, Pidgin, Swahili).

## Supported Languages (demo)

- English (`en`)
- Twi (`tw`)
- Hausa (`ha`)
- Pidgin English (`pcm`)
- Swahili (`sw`)

## License

MIT
