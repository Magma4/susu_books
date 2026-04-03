# Susu Books: An Offline Voice-First AI Ledger for the Informal Economy

## The Problem: 2.1 Billion People Invisible to Finance

Two billion people worldwide work in the informal economy — selling vegetables at dawn markets, running roadside stalls, tending small farms. In Ghana alone, the informal sector accounts for roughly 80% of employment. These workers are industrious, resourceful, and financially active. They buy stock, sell goods, track debts, and mentally calculate margins across dozens of transactions every day.

Yet almost none of this economic activity is recorded.

The consequences are severe. Without a transaction history, informal workers cannot access credit. Without credit, they cannot grow. A market woman who sells ₵5,000 of goods per week — and has done so for ten years — may still be refused a mobile-money loan because she has no documented revenue. The data exists in her head. It just isn't written down.

The barriers are not laziness or ignorance. They are practical: paper ledgers take time, require literacy and numeracy, and are lost in rain or fire. Smartphone apps assume comfort with touchscreens and English-language interfaces. Accounting software assumes an accountant. None of these tools fit into the life of someone who is simultaneously managing customers, handling cash, and watching their stall.

## The Solution: Speak Your Business

Susu Books is built on a single insight: **the most natural interface for recording a transaction is describing it out loud**, exactly as you would to a family member helping with the books.

> *"I bought 10 bags of rice from Kofi for 120 cedis each."*
> *"Sold 3 bags of rice at 180 to Maame."*
> *"Transport to market today cost 15 cedis."*

That's it. Tap once, speak naturally in English, Twi, Hausa, Pidgin, or Swahili, and Susu Books handles the rest — parsing the transaction, updating inventory, calculating profit, and storing everything locally with no internet required.

The name comes from *susu* (also spelled *esusu* or *asusu* depending on the language family) — a rotating savings collective practiced across West and Central Africa. Groups of traders pool money, each member taking turns receiving the full pot. Susu is built on radical trust and careful accounting. Susu Books is the digital extension of that tradition.

## Technical Architecture

The system has three layers, all designed to work entirely offline after a one-time setup.

**AI Layer — Gemma 4 via Ollama**: The core intelligence is Google's Gemma 4 model (31B-instruct, or the lighter 26B MoE variant) running locally through Ollama. Gemma 4's 128K context window lets the system maintain a full conversation history across dozens of exchanges in a single session. Its native multimodal capability enables receipt photograph processing — a user can photograph a handwritten receipt or a cardboard stock count, and Gemma 4 extracts every line item.

**Backend — FastAPI + SQLite**: A Python FastAPI server manages the AI orchestration loop, business logic, and data persistence. When Gemma 4 decides to record a transaction, it emits a structured tool call. The backend executes the corresponding function (one of seven: `record_purchase`, `record_sale`, `record_expense`, `check_inventory`, `daily_summary`, `weekly_report`, `export_credit_profile`), feeds the result back to Gemma 4, and lets the model compose a natural-language confirmation in the user's language. Inventory uses weighted-average-cost accounting — the same method taught in business schools, applied to a market stall.

**Frontend — Next.js 14 + Web Speech API**: The interface is a mobile-first single-page application designed for a 375px screen. The voice button is the largest interactive element on screen — intentionally. A state machine (idle → listening → processing → done) provides clear feedback at every step. When the microphone is unavailable or denied, the app surfaces a text input automatically. For the camera flow, the native `capture="environment"` attribute opens the back camera directly without a file picker.

The entire stack runs in Docker, with a one-command setup script that checks for Ollama, pulls the model if needed, seeds demo data, and starts both services. For field deployments on low-powered hardware, the Python backend can run without Docker on any machine with Python 3.11.

## Why Gemma 4 Specifically

Three properties of Gemma 4 made it the right choice for this problem.

**Multilingual capability without fine-tuning.** West African traders frequently code-switch mid-sentence — "I sold the rice, the price was fine, but the trotro fare expensive pass" mixes English and Pidgin naturally. Gemma 4 handles this without a specialized multilingual model or language detection preprocessing. In testing, it correctly parsed transactions containing Twi numerals embedded in English sentences.

**Structured output via tool calling.** Extracting a transaction from natural speech requires converting fuzzy natural language into precise structured fields: item name, quantity, unit, unit price, total, counterparty, transaction type. Gemma 4's tool-calling format provides exactly this bridge — the model decides when to call a function and fills the arguments from context, rather than requiring a rule-based NLP pipeline that would break on unusual phrasing.

**Efficient MoE architecture.** The `gemma4:26b-a4b-instruct` variant uses a mixture-of-experts design where only 4 billion parameters are active per inference. This makes it plausible to run on consumer hardware — a laptop with 16GB of unified memory, or a dedicated mini-PC at a cooperative's office serving multiple stalls on a local network. The full 31B dense model provides higher accuracy when hardware allows.

## Challenges and Design Decisions

**The zero-literacy constraint.** Early prototypes showed all the standard UI patterns — forms, dropdowns, confirmation dialogs. These were removed. The final design has three interactive elements in the main flow: the voice button, the camera button, and the language selector. Everything else is read-only display. The assumption is that a user who can operate a mobile phone can tap a large button and speak.

**Offline-first architecture.** The temptation to use a cloud API is real — it would make the system more capable and the demo more impressive. We explicitly chose not to. A market woman in a peri-urban neighborhood may have 2G connectivity, intermittent power, and a data budget measured in megabytes. Any system that requires a network call to process a transaction will fail her at exactly the moments she needs it most. The Gemma 4 model downloads once and runs forever.

**Trust and data ownership.** Informal economy workers have good reasons to distrust systems that capture their financial data and send it to unknown servers. Susu Books stores everything on the device running the application. There is no account creation, no sync, no telemetry. The credit profile export feature exists specifically so the user controls what data leaves their device and when.

**The cold-start problem.** A new user has no transaction history, so the dashboard is empty and the AI has no context. The seed script generates 14 days of realistic data for demo purposes. For real onboarding, the weekly report query ("how did I do this week?") produces a meaningful response after just a few recorded transactions, giving new users an immediate sense of value.

## Impact Thesis

The immediate output of Susu Books is a transaction ledger. The downstream outcomes extend further.

A recorded transaction history is the foundation of financial inclusion. Mobile money providers, microfinance institutions, and fintech lenders increasingly use alternative data to underwrite informal economy borrowers. A 90-day transaction history showing consistent revenue and positive margins is the kind of signal that unlocks a working-capital loan — the kind of loan that lets Ama buy a full pallet of rice at wholesale rather than ten bags at a time.

Beyond credit access, there are operational benefits that compound over time: understanding which items have the highest margins, recognizing seasonal patterns, identifying which customers are reliably profitable. These are insights that formal businesses take for granted and informal businesses currently have to carry in memory.

The multilingual, offline design also means the tool can spread through peer networks — one trader teaches another, the same way susu groups themselves spread. There is no onboarding fee, no monthly subscription, no requirement to have a bank account before you can start.

## Track and Evaluation Criteria

This submission is entered under the **Social Good** track of the Gemma 4 Good Hackathon.

The project demonstrates impact through direct utility: a working application that a real market trader can install and use today. The technical implementation showcases Gemma 4's function-calling capability in a production-ready architecture, its multimodal OCR on document photographs, and its multilingual comprehension across five languages. The offline-first design makes the social impact claim credible rather than theoretical — the system works in conditions where cloud-based alternatives would not.

Gemma 4 is not a prop in this project. It is the core mechanism by which natural spoken language becomes structured financial data. Without the model's ability to parse intent, extract fields, and confirm in natural language, the entire user experience collapses into a conventional form. With it, bookkeeping becomes as easy as talking to a friend.

---

*Susu Books — because every transaction deserves to be remembered.*
