#!/usr/bin/env python3
"""
Susu Books - Training Bundle Preparer
Gathers all necessary files for fine-tuning in a cloud environment (Kaggle/Colab).
"""

import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = REPO_ROOT / "susu_training_bundle"
ZIP_PATH = REPO_ROOT / "susu_training_bundle_v5.zip"

def main():
    print(f"Preparing training bundle at {BUNDLE_DIR}...")
    
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)
    BUNDLE_DIR.mkdir()

    # 1. Create backend dependency folder
    backend_bundle = BUNDLE_DIR / "backend"
    backend_bundle.mkdir()
    shutil.copy(REPO_ROOT / "backend" / "ai_contract.py", backend_bundle / "ai_contract.py")

    # 2. Copy training scripts and requirements
    training_src = REPO_ROOT / "training"
    scripts = [
        "train_unsloth.py",
        "synthetic_data.py",
        "import_ghana_nlp.py",
        "benchmark_extraction.py",
        "requirements.txt"
    ]
    
    for script in scripts:
        src = training_src / script
        if src.exists():
            shutil.copy(src, BUNDLE_DIR / script)
        else:
            print(f"Warning: {script} not found in training/ folder.")

    # 3. Copy pre-generated data so Kaggle can start training immediately.
    data_src = training_src / "data"
    if data_src.exists():
        shutil.copytree(data_src, BUNDLE_DIR / "data")

    # 4. Create a README for the bundle
    readme = BUNDLE_DIR / "RUN_ME_FIRST.md"
    readme.write_text(r"""# Susu Books - Kaggle Training Bundle

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
""", encoding="utf-8")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with ZipFile(ZIP_PATH, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(BUNDLE_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(REPO_ROOT))

    print("\nBundle prepared successfully!")
    print(f"Folder: {BUNDLE_DIR}")
    print(f"Zip   : {ZIP_PATH}")

if __name__ == "__main__":
    main()
