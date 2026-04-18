# Susu Books: Offline Voice-First Bookkeeping for the Informal Economy

## Problem

Informal economy workers run real businesses, but most of their financial history never gets recorded. A market trader may buy stock at dawn, sell all day, pay transport and market fees, and still end the day with no reliable record of revenue, costs, or profit. That missing history blocks better pricing, better restocking decisions, and access to credit. The issue is not that existing users do not want bookkeeping. It is that most bookkeeping tools assume literacy, time, stable internet, and comfort with English-language forms.

Susu Books starts from a different assumption: the easiest way to record a business transaction is to say it out loud.

## Solution

Susu Books is an offline, voice-first AI business copilot for market women, street vendors, and smallholder farmers. A user taps one large button and says something natural like:

- `I bought 10 bags of rice from Kofi for 120 cedis each`
- `Sold 3 bags of rice at 180 to Maame`
- `Transport to market today cost 15 cedis`

The system extracts structured data, updates the ledger, adjusts inventory, computes profit, and speaks back a short confirmation in the user’s selected language. Users can also upload photographs of receipts, handwritten notes, and product labels for image-based extraction.

Everything runs locally: Gemma 4 through Ollama, a FastAPI backend, and a SQLite database. There are no cloud dependencies in the core product flow.

## Hybrid Multilingual Design

During development, we discovered that Gemma 4's text generation quality in low-resource languages like Twi and Hausa is unreliable — grammatically incorrect outputs would erode trust with the exact users we're trying to serve. Rather than shipping broken multilingual generation, we designed a hybrid architecture: Gemma 4's multilingual understanding capabilities extract structured transaction data from speech in any language, while human-verified response templates guarantee grammatically correct, culturally appropriate output. This approach is more honest, more reliable, and more respectful of the languages we serve. It also makes the system trivially extensible — adding a new language requires only a new JSON template file verified by a native speaker, not retraining a model.

That decision shaped the whole product. Gemma 4 is responsible for understanding the input and returning function calls only. The backend is responsible for business logic and persistence. The final user-facing sentence comes from deterministic templates in English, Twi, Hausa, Nigerian Pidgin, and Swahili. This gives us the multilingual reach of Gemma’s understanding without pretending the model is a polished writer in every market language.

## Technical Architecture

The system has three layers.

**Frontend:** A Next.js 14 application provides a three-zone dashboard: live ledger feed, alerts and summaries, and a large voice-and-camera action area. The interface is intentionally simple, mobile-first, and low-text. Voice input uses the browser Web Speech API. Voice output uses SpeechSynthesis when the device has a usable local voice and falls back cleanly when it does not.

**Backend:** FastAPI exposes `POST /api/chat`, `POST /api/chat/image`, reporting endpoints, inventory endpoints, and transaction CRUD. SQLAlchemy writes to SQLite, which runs in WAL mode with a busy timeout to reduce lock contention during UI polling. Business logic is split into services for ledger operations, inventory tracking, reporting, Gemma orchestration, and template rendering.

**AI Layer:** Gemma 4 runs locally through Ollama. The backend sends a strict system prompt plus eight tool definitions: `record_purchase`, `record_sale`, `record_expense`, `check_inventory`, `daily_summary`, `weekly_report`, `export_credit_profile`, and `clarify_input`. Gemma 4 never returns free-form answers in the production flow. It returns function calls, and the backend executes them.

The image flow works similarly. An uploaded receipt or handwritten note is sent to Gemma 4 as an image plus prompt, Gemma emits tool calls for extracted transactions, and the backend executes them just like spoken input.

## Why Gemma 4

Gemma 4 fits this problem for three reasons.

First, it has strong multilingual understanding. Informal market speech is messy in exactly the way normal life is messy: users code-switch, drop units, mix local terms with English, and describe totals indirectly. Gemma 4 is good at interpreting that kind of intent, especially when paired with tool calling and domain-specific instructions.

Second, tool calling is the right abstraction for bookkeeping. The task is not open-ended conversation. The task is turning speech into structured actions with fields like item, quantity, unit price, total amount, counterparty, and category. Tool calling gives us a clean bridge from natural language to deterministic ledger updates.

Third, Gemma 4 can run locally through Ollama. That matters because this product is designed for unreliable connectivity, privacy-sensitive users, and environments where data costs matter. A bookkeeping assistant that fails whenever the network drops is not a serious tool for the people we are building for.

## Real Utility

Susu Books is not just a transcription demo. It maintains live inventory with weighted-average-cost accounting, flags low stock, computes daily and weekly performance, and exports a lender-friendly credit profile. That last feature matters because a consistent transaction history can become proof of business activity for microfinance or mobile-money lending workflows.

For the hackathon demo, the repository includes:

- Docker Compose for backend and frontend integration
- a one-command `setup.sh` that checks Ollama, chooses the best available Gemma 4 model, seeds demo data, and starts the app
- a 14-day seed dataset for Ama, an Accra trader, with realistic purchases, sales, expenses, low-stock alerts, and cached summaries
- an Unsloth LoRA pipeline that generates synthetic multilingual training data, benchmarks extraction accuracy, and exports a GGUF model back into Ollama
- a demo mode and a separate three-minute video script

This makes the project easy to judge as a real working system rather than a slideware concept.

## Key Design Decisions

The first design constraint was low literacy. We removed form-heavy patterns and made voice the default path. The second was offline reliability. We avoided cloud APIs entirely in the main loop. The third was trust. Every trader-facing reply must be short, predictable, and grammatically correct in the chosen language. That is why templates are such a central part of the architecture rather than a cosmetic add-on.

We also treated failure modes seriously. The backend returns structured validation and server errors, rejects unsupported image uploads, and keeps audit fields like `raw_input`, `language`, and `confidence` for transparency. The frontend degrades gracefully when speech recognition or speech synthesis support is weak on a given device.

## Impact

The immediate outcome is better bookkeeping. The longer-term outcome is visibility. A trader with ninety days of consistent records has something powerful: evidence. Evidence of revenue, evidence of margin, evidence of business discipline. That can unlock better restocking decisions, better cash planning, and eventually access to working capital.

Susu Books fits the Digital Equity and Inclusivity spirit of the hackathon because it does not ask users to adapt to formal software norms. Instead, it adapts AI to the way informal businesses already work: local language, spoken workflow, low bandwidth, and practical trust.

Gemma 4 is central to that value. It is the multilingual extraction engine that turns everyday speech into structured economic memory.
