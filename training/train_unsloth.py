"""
Train a Susu Books extraction adapter with Unsloth LoRA.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "training" / "data"
DEFAULT_RUN_DIR = REPO_ROOT / "training" / "runs" / "susu-books-lora"
DEFAULT_MERGED_DIR = REPO_ROOT / "training" / "exports" / "susu-books-merged"
DEFAULT_GGUF_DIR = REPO_ROOT / "training" / "exports" / "susu-books-gguf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune Gemma 4 for Susu Books extraction with Unsloth LoRA.")
    parser.add_argument("--model-name", default="unsloth/gemma-4-e4b-it")
    parser.add_argument("--train-file", type=Path, default=DEFAULT_DATA_DIR / "synthetic_train_sft.jsonl")
    parser.add_argument("--val-file", type=Path, default=DEFAULT_DATA_DIR / "synthetic_val_sft.jsonl")
    parser.add_argument("--benchmark-file", type=Path, default=DEFAULT_DATA_DIR / "synthetic_val_raw.jsonl")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--merged-dir", type=Path, default=DEFAULT_MERGED_DIR)
    parser.add_argument("--gguf-dir", type=Path, default=DEFAULT_GGUF_DIR)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--warmup-ratio", type=float, default=0.05)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--lr-scheduler", default="cosine")
    parser.add_argument("--save-steps", type=int, default=100)
    parser.add_argument("--eval-steps", type=int, default=100)
    parser.add_argument("--logging-steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--report-to", default="none")
    parser.add_argument("--gguf-quant", default="q4_k_m")
    parser.add_argument("--skip-merge", action="store_true")
    parser.add_argument("--skip-gguf", action="store_true")
    parser.add_argument("--run-benchmark", action="store_true")
    return parser.parse_args()


def write_ollama_modelfile(directory: Path, base_system_prompt: str, quant_file_name: str) -> Path:
    modelfile = directory / "Modelfile"
    modelfile.write_text(
        "\n".join(
            [
                f"FROM ./{quant_file_name}",
                "",
                f'SYSTEM """{base_system_prompt}"""',
                "",
                "# Susu Books fine-tuned extraction model",
                "PARAMETER temperature 0.1",
                "PARAMETER top_p 0.85",
                "PARAMETER repeat_penalty 1.1",
                "PARAMETER num_ctx 4096",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return modelfile


def main() -> None:
    args = parse_args()

    try:
        import torch
        from datasets import load_dataset
        from trl import SFTConfig, SFTTrainer
        from unsloth import FastLanguageModel, is_bfloat16_supported
    except ImportError as exc:
        raise SystemExit(
            "Training dependencies are missing. Install training/requirements.txt in a Kaggle or GPU environment first."
        ) from exc

    import sys

    backend_dir = REPO_ROOT / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from ai_contract import EXTRACTION_SYSTEM_PROMPT

    if not args.train_file.exists() or not args.val_file.exists():
        raise SystemExit(
            "Training data not found. Run `python training/synthetic_data.py` first."
        )

    dataset = load_dataset(
        "json",
        data_files={"train": str(args.train_file), "validation": str(args.val_file)},
    )

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model_name,
        max_seq_length=args.max_seq_length,
        dtype=None,
        load_in_4bit=args.load_in_4bit,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        args=SFTConfig(
            dataset_text_field="text",
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.gradient_accumulation,
            warmup_ratio=args.warmup_ratio,
            num_train_epochs=args.epochs,
            learning_rate=args.learning_rate,
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            logging_steps=args.logging_steps,
            eval_strategy="steps",
            eval_steps=args.eval_steps,
            save_strategy="steps",
            save_steps=args.save_steps,
            save_total_limit=2,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            optim="adamw_8bit",
            weight_decay=args.weight_decay,
            lr_scheduler_type=args.lr_scheduler,
            max_grad_norm=args.max_grad_norm,
            seed=args.seed,
            output_dir=str(args.output_dir),
            report_to=args.report_to,
            max_seq_length=args.max_seq_length,
        ),
    )

    trainer_stats = trainer.train()

    model.save_pretrained(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))

    summary: dict[str, Any] = {
        "model_name": args.model_name,
        "train_examples": len(dataset["train"]),
        "validation_examples": len(dataset["validation"]),
        "train_runtime_seconds": trainer_stats.metrics.get("train_runtime"),
        "train_loss": trainer_stats.metrics.get("train_loss"),
        "epochs": args.epochs,
        "effective_batch_size": args.batch_size * args.gradient_accumulation,
        "output_dir": str(args.output_dir),
    }

    if torch.cuda.is_available():
        summary["peak_vram_gb"] = round(torch.cuda.max_memory_allocated() / 1024**3, 2)

    if not args.skip_merge:
        args.merged_dir.mkdir(parents=True, exist_ok=True)
        if not hasattr(model, "save_pretrained_merged"):
            raise RuntimeError("Installed Unsloth build does not expose save_pretrained_merged.")
        model.save_pretrained_merged(str(args.merged_dir), tokenizer, save_method="merged_16bit")
        summary["merged_dir"] = str(args.merged_dir)

    if not args.skip_gguf:
        args.gguf_dir.mkdir(parents=True, exist_ok=True)
        if not hasattr(model, "save_pretrained_gguf"):
            raise RuntimeError("Installed Unsloth build does not expose save_pretrained_gguf.")
        model.save_pretrained_gguf(str(args.gguf_dir), tokenizer, quantization_method=args.gguf_quant)
        gguf_files = sorted(args.gguf_dir.glob("*.gguf"))
        if gguf_files:
            modelfile = write_ollama_modelfile(args.gguf_dir, EXTRACTION_SYSTEM_PROMPT, gguf_files[0].name)
            summary["gguf_dir"] = str(args.gguf_dir)
            summary["ollama_modelfile"] = str(modelfile)

    if args.run_benchmark:
        if not args.benchmark_file.exists():
            raise RuntimeError(f"Benchmark file not found: {args.benchmark_file}")
        from benchmark_extraction import evaluate_model

        benchmark_metrics = evaluate_model(
            model_name=str(args.output_dir),
            dataset_path=args.benchmark_file,
            max_seq_length=args.max_seq_length,
            load_in_4bit=args.load_in_4bit,
            batch_size=min(args.batch_size * 2, 8),
            limit=0,
        )
        summary["benchmark"] = benchmark_metrics
        benchmark_path = args.output_dir / "benchmark.json"
        benchmark_path.write_text(json.dumps(benchmark_metrics, indent=2) + "\n", encoding="utf-8")

    summary_path = args.output_dir / "training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("Training complete.")
    print(f"  Adapter dir : {args.output_dir}")
    if summary.get("merged_dir"):
        print(f"  Merged dir  : {summary['merged_dir']}")
    if summary.get("gguf_dir"):
        print(f"  GGUF dir    : {summary['gguf_dir']}")
    print(f"  Summary     : {summary_path}")


if __name__ == "__main__":
    main()
