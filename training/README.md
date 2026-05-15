# Susu Books Fine-Tuning

This folder contains the Phase 4 pipeline for improving multilingual extraction accuracy with Unsloth LoRA.

The script-based workflow in this folder is the source of truth for fine-tuning. The older notebook under `notebooks/` is exploratory and may lag behind the live backend contract.

## Files

- `synthetic_data.py`: generates multilingual train and validation datasets for the live eight-tool extraction contract
- `train_unsloth.py`: fine-tunes a Gemma 4 instruction model with LoRA
- `benchmark_extraction.py`: scores parse rate, function accuracy, argument accuracy, and exact match on the held-out validation set
- `requirements.txt`: GPU-side training dependencies

## 1. Generate Synthetic Data

From the repo root:

```bash
python3 training/synthetic_data.py --output-dir training/data --train-examples 2700 --val-examples 300
```

This writes:

- `training/data/synthetic_train_raw.jsonl`
- `training/data/synthetic_val_raw.jsonl`
- `training/data/synthetic_train_sft.jsonl`
- `training/data/synthetic_val_sft.jsonl`
- `training/data/manifest.json`
- `training/data/preview.json`

The generator is balanced across:

- 5 languages: English, Twi, Hausa, Nigerian Pidgin, Swahili
- 8 tool intents: purchases, sales, expenses, inventory checks, daily summaries, weekly reports, credit export, clarify

It also injects realistic variation:

- code-switching and market phrasing
- local item names normalized to English labels
- total-only and unit-price-only transaction descriptions
- supplier and customer names from Ghana, Nigeria, and Kenya

## 2. Import External Real-World Data (Ghana-NLP)

To improve Twi extraction quality with real human-written market grammar, you can import data from Ghana-NLP:

```bash
python3 training/import_ghana_nlp.py --output training/data/ghana_nlp_sft.jsonl
```

This filters the Twi-English parallel text for transactional keywords and maps them to the Susu Books tool contract. You can append this to your training dataset:

```bash
cat training/data/ghana_nlp_sft.jsonl >> training/data/synthetic_train_sft.jsonl
```

## 3. Install Training Dependencies

In a GPU environment such as Kaggle:

```bash
pip install -r training/requirements.txt
```

## Kaggle ASAP Path

The fastest Kaggle route is to upload the generated bundle zip:

```bash
python3 training/prepare_bundle.py
```

Upload [susu_training_bundle_v5.zip](../susu_training_bundle_v5.zip) to a Kaggle Notebook as an input dataset, enable a GPU accelerator, then run:

```bash
cd /kaggle/working
unzip -q /kaggle/input/*/susu_training_bundle_v5.zip -d /kaggle/working || true
cd /kaggle/working/susu_training_bundle
pip install -q -r requirements.txt
```

Then start with the smallest practical Gemma 4 adapter run:

```bash
python train_unsloth.py \
  --model-name unsloth/gemma-4-e2b-it \
  --train-file data/synthetic_train_sft.jsonl \
  --val-file data/synthetic_val_sft.jsonl \
  --benchmark-file data/synthetic_val_raw.jsonl \
  --output-dir runs/susu-books-lora \
  --merged-dir exports/susu-books-merged \
  --gguf-dir exports/susu-books-gguf \
  --load-in-4bit \
  --run-benchmark
```

If Kaggle runs out of memory, use the lighter command:

```bash
python train_unsloth.py \
  --model-name unsloth/gemma-4-e2b-it \
  --train-file data/synthetic_train_sft.jsonl \
  --val-file data/synthetic_val_sft.jsonl \
  --benchmark-file data/synthetic_val_raw.jsonl \
  --output-dir runs/susu-books-lora \
  --batch-size 2 \
  --gradient-accumulation 8 \
  --max-seq-length 1536 \
  --skip-merge \
  --skip-gguf \
  --load-in-4bit \
  --run-benchmark
```

## 4. Train with Unsloth LoRA

```bash
python training/train_unsloth.py \
  --model-name unsloth/gemma-4-e4b-it \
  --train-file training/data/synthetic_train_sft.jsonl \
  --val-file training/data/synthetic_val_sft.jsonl \
  --benchmark-file training/data/synthetic_val_raw.jsonl \
  --output-dir training/runs/susu-books-lora \
  --merged-dir training/exports/susu-books-merged \
  --gguf-dir training/exports/susu-books-gguf \
  --load-in-4bit \
  --run-benchmark
```

Default training setup:

- base model: `unsloth/gemma-4-e4b-it`
- LoRA rank: `16`
- LoRA alpha: `32`
- LoRA dropout: `0.05`
- epochs: `3`
- effective batch size: `16`
- learning rate: `2e-4`

## 5. Benchmark a Model Separately

```bash
python training/benchmark_extraction.py \
  --model-name training/runs/susu-books-lora \
  --dataset training/data/synthetic_val_raw.jsonl \
  --load-in-4bit \
  --output-json training/runs/susu-books-lora/benchmark.json
```

Metrics:

- parse rate
- function name accuracy
- argument match accuracy across all gold arguments
- exact match accuracy
- per-language and per-intent breakdowns

## 6. Load the Fine-Tuned Model in Ollama

After training, `train_unsloth.py` writes a GGUF export and `Modelfile`.

From the GGUF directory:

```bash
ollama create susu-books-ft -f Modelfile
```

Then update `backend/.env`:

```bash
OLLAMA_MODEL=susu-books-ft
```

Restart the backend and Susu Books will use the fine-tuned extractor.

## Notes

- The training data mirrors the live backend prompt and tool schema through [backend/ai_contract.py](../backend/ai_contract.py).
- The pipeline fine-tunes extraction behavior only. Trader-facing responses still come from human-verified templates.
- Generated adapters, merged checkpoints, and GGUF exports should be published with benchmark JSON for the hackathon submission.
