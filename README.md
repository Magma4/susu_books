# Susu Books

Offline, voice-first AI bookkeeping for market traders, street vendors, and smallholder farmers.

Susu Books lets a trader speak naturally about purchases, sales, and expenses in English, Twi, Hausa, Nigerian Pidgin, Swahili, or mixed market speech. Gemma 4 runs locally through Ollama, extracts structured transaction data through tool calls, and the backend updates the ledger, inventory, and reports. Every user-facing reply comes from human-written language templates, so the app stays trustworthy even in low-resource languages.

## What Makes It Different

- Voice-first UX with one primary action: tap and talk.
- Fully offline after setup: Ollama, FastAPI, and SQLite all run locally.
- Hybrid multilingual architecture: Gemma 4 extracts; templates speak back.
- Receipt and handwritten note support through local image upload.
- Weighted-average-cost inventory tracking, daily summaries, weekly reports, and lender-friendly credit profile export.
- Warm, touch-friendly dashboard designed for low-literacy, mobile-first use.

## Hybrid Architecture

Susu Books deliberately separates understanding from response generation:

1. The trader speaks in any supported language or code-switched mix.
2. Gemma 4 receives the message with a strict extraction prompt and tool schemas.
3. Gemma 4 returns tool calls only, such as `record_purchase` or `daily_summary`.
4. FastAPI executes the tool, writes to SQLite, and computes the business result.
5. The backend renders the final reply from a verified language template.

That means the model never improvises trader-facing Twi or Hausa text. We use Gemma 4 where it is strongest, then hand off the final wording to deterministic templates the user can learn to trust.

## Core Functions

The extraction engine can call exactly these eight tools:

- `record_purchase`
- `record_sale`
- `record_expense`
- `check_inventory`
- `daily_summary`
- `weekly_report`
- `export_credit_profile`
- `clarify_input`

## Demo Flow

The seeded demo data represents Ama, a market trader in Accra, with 14 days of realistic trading history. The frontend also includes a guided demo mode that auto-plays a day in the market.

Suggested live demo sequence:

1. Ask: `I bought 10 bags of rice from Kofi for 120 cedis each`
2. Ask: `Sold 3 bags of rice at 180 cedis each to Maame`
3. Ask: `Transport to market today cost 15 cedis`
4. Ask in Pidgin: `How today go?`
5. Ask in Twi: `Me onion no aka sen?`
6. Upload a receipt or handwritten note through the camera flow

There is also a submission-friendly runbook in [demo-script.md](demo-script.md).

## Stack

- Frontend: Next.js 14, React, TypeScript, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, SQLite
- AI: Gemma 4 through Ollama tool calling
- Voice input: Browser Web Speech API
- Voice output: Browser SpeechSynthesis API
- Vision: Gemma 4 multimodal image understanding through Ollama
- Templates: JSON translation files under [backend/templates](backend/templates)

## Quick Start

### Option 1: One-command setup

```bash
git clone https://github.com/YOUR_USERNAME/susu-books.git
cd susu-books
bash setup.sh
```

What `setup.sh` does:

- verifies Ollama is installed and reachable
- prefers `gemma4:31b-instruct`
- falls back to `gemma4:26b-a4b-instruct`
- falls back again to `gemma4:e2b` on smaller machines
- prepares backend and frontend environment files
- starts Docker services by default
- seeds two weeks of demo data unless `--no-seed` is passed

Flags:

- `--dev`: run backend and frontend locally with hot reload
- `--no-docker`: skip Docker and use Python plus npm directly
- `--no-seed`: start with an empty database

### Option 2: Docker Compose directly

Requirements:

- Ollama installed on the host and reachable at `http://localhost:11434`
- one Gemma 4 model pulled locally

```bash
ollama pull gemma4:31b-instruct
docker compose up --build
```

The backend container connects to host Ollama through `host.docker.internal`, and SQLite is stored in the named Docker volume `susu-data`.

Production-minded defaults are already wired into `docker-compose.yml`:

- backend docs are disabled unless `API_DOCS_ENABLED=true`
- security headers stay enabled
- AI endpoints are rate-limited
- containers run read-only with a writable `/data` volume for SQLite and `/tmp` tmpfs
- the backend runs as a non-root user

### Option 3: Manual local development

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
uvicorn main:app --reload --port 8000

# Frontend
cd ../frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open:

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Production Deploy Notes

Before you put Susu Books on a public URL, set these values explicitly:

- `NEXT_PUBLIC_API_URL` to your HTTPS backend origin
- `ALLOWED_HOSTS` to your real domain names
- `CORS_ORIGINS` to the frontend origin you will serve
- `API_DOCS_ENABLED=false`
- `OLLAMA_MODEL` to the exact Gemma 4 model actually installed on that machine

You should also:

- terminate TLS with a reverse proxy such as Nginx, Caddy, or Cloudflare Tunnel
- keep Ollama on the same machine or private network as the backend
- back up the `/data` Docker volume or `backend/susu_books.db` regularly
- use a machine with enough RAM for your chosen Gemma 4 variant

## Verification

Backend checks:

```bash
cd backend
.venv/bin/python -m unittest discover -s ../tests -p "test_*.py" -v
python3 -m py_compile *.py routers/*.py services/*.py
```

Frontend checks:

```bash
cd frontend
npm run type-check
npm run lint
npm run build
```

## API Surface

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/chat` | Voice or text message -> tool calls -> template response |
| `POST` | `/api/chat/image` | Image OCR and extraction through Gemma 4 vision |
| `GET` | `/api/health` | Backend, Ollama, and database health |
| `GET` | `/api/languages` | Supported UI/template languages |
| `GET` | `/api/transactions` | Transaction feed with filters |
| `GET` | `/api/inventory` | Current stock levels |
| `GET` | `/api/inventory/check/alerts` | Low-stock and zero-stock alerts |
| `GET` | `/api/summary/daily` | Daily P&L summary |
| `GET` | `/api/summary/weekly` | Seven-day report |
| `GET` | `/api/export/credit-profile` | Credit profile export |
| `GET` | `/api/export/transactions.csv` | Download ledger as CSV |
| `GET` | `/api/export/backup.json` | Download full JSON backup |

## Error Handling

Phase 3 adds submission-grade error handling on the backend:

- unsupported image types return `415`
- oversized uploads return `413`
- bad request payloads return structured `422` validation errors
- known application failures return structured `4xx` or `502` responses
- unhandled exceptions return a consistent `500` JSON payload and are logged server-side
- SQLite runs with WAL mode and a busy timeout to reduce lock contention during UI polling

The frontend already degrades gracefully when:

- microphone permission is denied
- no strong local TTS voice exists for the selected language
- Ollama is offline or the configured model is missing

## Seed Data

The demo seed script at [backend/seed.py](backend/seed.py) creates:

- 14 days of transactions for Ama
- purchases, sales, and operating expenses
- realistic low-stock alerts for palm oil and tomatoes
- cached daily summaries for faster dashboard load
- inventory rebuilt through the same services used in production

This is intentional: the demo data exercises the exact ledger, inventory, and reporting paths used by live voice transactions.

## Fine-Tuning

Phase 4 adds an Unsloth fine-tuning pipeline under [training](training) for improving extraction accuracy without changing the hybrid template-based response design.

It includes:

- a synthetic multilingual dataset generator covering the live eight-tool contract
- balanced train and validation data in [training/data](training/data)
- an Unsloth LoRA training script in [training/train_unsloth.py](training/train_unsloth.py)
- a benchmark script in [training/benchmark_extraction.py](training/benchmark_extraction.py)
- end-to-end instructions in [training/README.md](training/README.md)

The fine-tuned model is still extraction-only. User-facing responses remain deterministic templates.

## Project Structure

```text
susu-books/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── seed.py
│   ├── templates/
│   │   ├── en.json
│   │   ├── tw.json
│   │   ├── ha.json
│   │   ├── pcm.json
│   │   └── sw.json
│   ├── routers/
│   └── services/
├── frontend/
├── training/
├── docker-compose.yml
├── setup.sh
├── demo-script.md
└── writeup.md
```

## Language Support

Current response-template languages:

- English: `en`
- Twi: `tw`
- Hausa: `ha`
- Nigerian Pidgin: `pcm`
- Swahili: `sw`

Speech recognition and speech synthesis depend on the browser and installed device voices, so voice quality varies by platform. The app still works with typed input even when speech services are limited.

## Submission Notes

For the Gemma 4 Good Hackathon submission:

- the live demo should show the seeded Ama scenario plus one live multilingual transaction
- the code repository should link directly to this repo
- the Kaggle writeup can start from [writeup.md](writeup.md)
- the video outline can start from [demo-script.md](demo-script.md)

Susu Books is designed to be honest about the limits of current multilingual generation while still delivering a genuinely useful offline AI product.
