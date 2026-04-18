# Susu Books Demo Script

Three-minute demo outline for the Gemma 4 Good Hackathon submission video.

## 0:00-0:20 — The Problem

Show a market stall or ledger view.

Voiceover:

`Millions of informal workers run real businesses every day, but their transactions live only in memory. No records means no insight, no proof of income, and no access to credit.`

## 0:20-0:40 — The Product

Show the Susu Books home screen with the large voice button.

Voiceover:

`Susu Books is an offline, voice-first AI business copilot. A trader taps once, speaks naturally in her own language, and Susu Books updates her books instantly on-device.`

## 0:40-1:20 — Live Voice Flow

Record three short interactions:

1. `I bought 10 bags of rice from Kofi for 120 cedis each`
2. `Sold 3 bags of rice at 180 cedis each to Maame`
3. `Transport to market today cost 15 cedis`

On screen, show:

- function-call transparency if visible
- ledger feed updating
- inventory and summary changes

Voiceover:

`Gemma 4 is not writing the final answer here. It is extracting structured business data through tool calls, and the backend applies real accounting logic to the ledger and inventory.`

## 1:20-1:50 — Multilingual Trust

Switch language and ask:

- Pidgin: `How today go?`
- Twi: `Me onion no aka sen?`

Voiceover:

`We discovered that low-resource language generation can be unreliable. So we built a hybrid system: Gemma 4 understands multilingual speech and extracts the data, but trader-facing replies come from human-verified templates. That keeps the system honest and trustworthy.`

## 1:50-2:15 — Receipt / OCR Flow

Upload a receipt or handwritten note photo and show extracted transactions entering the ledger.

Voiceover:

`Susu Books also reads receipts, handwritten notes, and product labels locally through Gemma 4 vision support in Ollama.`

## 2:15-2:40 — Business Intelligence

Show:

- daily summary
- weekly trend
- low-stock alerts
- credit profile export

Voiceover:

`The result is more than bookkeeping. Traders get stock alerts, profit summaries, weekly trends, and a transaction history they can eventually use for financial access.`

## 2:40-3:00 — Close

Show the full dashboard and offline architecture graphic or terminal with local services running.

Voiceover:

`Everything runs locally: Gemma 4 through Ollama, FastAPI, SQLite, and a voice-first web app. Susu Books turns speech into trustworthy records for workers the formal financial system still overlooks.`
