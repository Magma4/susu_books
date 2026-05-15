# Susu Books - Kaggle Training Bundle

This bundle contains everything needed to fine-tune Gemma 4 for Susu Books on Kaggle.

## Fast Kaggle Path

1. Upload `susu_training_bundle_v5.zip` as a Kaggle Notebook input dataset, or upload/extract it into `/kaggle/working`.
2. Turn on a GPU accelerator in Notebook settings. T4 x2 is the practical minimum; P100/A100 is better.
3. Run these cells:

   ```bash
   cd /kaggle/working
   unzip -q /kaggle/input/*/susu_training_bundle_v5.zip -d /kaggle/working || true
   cd /kaggle/working/susu_training_bundle
   pip install -q -r requirements.txt
   ```

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

## If Memory Fails

Use this lighter command:

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

## Optional Data Refresh

The bundle already includes synthetic data. Regenerate only if you want a fresh split:

```bash
python synthetic_data.py --output-dir data --train-examples 2700 --val-examples 300
```

You can also add Ghana-NLP examples if the notebook has internet enabled:

```bash
python import_ghana_nlp.py --output data/ghana_nlp_sft.jsonl
cat data/ghana_nlp_sft.jsonl >> data/synthetic_train_sft.jsonl
```

## Output Files

- `runs/susu-books-lora`: LoRA adapter and training summary
- `runs/susu-books-lora/benchmark.json`: extraction benchmark metrics
- `exports/susu-books-gguf`: Ollama-ready GGUF and `Modelfile` if export succeeds
