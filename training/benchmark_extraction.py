"""
Benchmark a base or fine-tuned Gemma model on the Susu Books validation set.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark extraction accuracy on the Susu Books validation set.")
    parser.add_argument("--model-name", required=True, help="Hugging Face model id or local adapter/model path.")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to synthetic_val_raw.jsonl")
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on evaluation rows.")
    parser.add_argument("--output-json", type=Path, default=None, help="Optional JSON file for benchmark metrics.")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def parse_tool_call_from_text(text: str) -> dict[str, Any] | None:
    match = re.search(r"<tool_call>\s*({.*?})\s*</tool_call>", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def normalize_scalar(value: Any) -> str:
    return str(value).strip().lower().replace("_", " ").replace("-", " ")


def values_match(predicted: Any, expected: Any) -> bool:
    if isinstance(expected, (int, float)):
        try:
            predicted_number = float(predicted)
            expected_number = float(expected)
        except (TypeError, ValueError):
            return False
        denominator = abs(expected_number) if abs(expected_number) > 1e-6 else 1.0
        return abs(predicted_number - expected_number) / denominator <= 0.01
    return normalize_scalar(predicted) == normalize_scalar(expected)


def argument_match_score(predicted: dict[str, Any], expected: dict[str, Any]) -> float:
    if not expected:
        return 1.0
    correct = 0
    for key, expected_value in expected.items():
        if key in predicted and values_match(predicted[key], expected_value):
            correct += 1
    return correct / len(expected)


def evaluate_model(
    *,
    model_name: str,
    dataset_path: Path,
    max_seq_length: int,
    load_in_4bit: bool,
    batch_size: int,
    limit: int,
) -> dict[str, Any]:
    try:
        import torch
        from unsloth import FastLanguageModel
    except ImportError as exc:
        raise RuntimeError(
            "Unsloth is not installed in this environment. Install training/requirements.txt first."
        ) from exc

    rows = load_jsonl(dataset_path)
    if limit > 0:
        rows = rows[:limit]
    if not rows:
        raise RuntimeError(f"No evaluation rows found in {dataset_path}")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=load_in_4bit,
        dtype=None,
    )
    FastLanguageModel.for_inference(model)

    function_correct = 0
    exact_match = 0
    parse_success = 0
    argument_scores: list[float] = []
    per_language: dict[str, list[float]] = defaultdict(list)
    per_intent: dict[str, list[float]] = defaultdict(list)

    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        prompts = []
        for row in batch:
            messages = row["messages"]
            prompts.append(
                f"<start_of_turn>user\n{messages[0]['content']}\n\n{messages[1]['content']}<end_of_turn>\n"
                "<start_of_turn>model\n"
            )

        encoded = tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_seq_length,
        ).to(model.device)

        with torch.no_grad():
            output = model.generate(
                **encoded,
                max_new_tokens=256,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )

        decoded = tokenizer.batch_decode(output[:, encoded["input_ids"].shape[1] :], skip_special_tokens=True)

        for predicted_text, row in zip(decoded, batch):
            gold_function = row["messages"][2]["tool_calls"][0]["function"]["name"]
            gold_arguments = row["messages"][2]["tool_calls"][0]["function"]["arguments"]
            metadata = row["_meta"]
            parsed = parse_tool_call_from_text(predicted_text)

            if parsed is None:
                score = 0.0
            else:
                parse_success += 1
                predicted_function = parsed.get("name", "")
                predicted_arguments = parsed.get("arguments", {})
                if isinstance(predicted_arguments, str):
                    try:
                        predicted_arguments = json.loads(predicted_arguments)
                    except json.JSONDecodeError:
                        predicted_arguments = {}

                if predicted_function == gold_function:
                    function_correct += 1
                    score = argument_match_score(
                        predicted_arguments if isinstance(predicted_arguments, dict) else {},
                        gold_arguments,
                    )
                    if score == 1.0:
                        exact_match += 1
                else:
                    score = 0.0

            argument_scores.append(score)
            per_language[metadata["language"]].append(score)
            per_intent[metadata["intent"]].append(score)

    total = len(rows)
    metrics = {
        "examples": total,
        "parse_rate": round(parse_success / total, 4),
        "function_name_accuracy": round(function_correct / total, 4),
        "argument_match_accuracy": round(sum(argument_scores) / total, 4),
        "exact_match_accuracy": round(exact_match / total, 4),
        "per_language_argument_match": {
            language: round(sum(scores) / len(scores), 4)
            for language, scores in sorted(per_language.items())
        },
        "per_intent_argument_match": {
            intent: round(sum(scores) / len(scores), 4)
            for intent, scores in sorted(per_intent.items())
        },
    }
    return metrics


def main() -> None:
    args = parse_args()
    metrics = evaluate_model(
        model_name=args.model_name,
        dataset_path=args.dataset,
        max_seq_length=args.max_seq_length,
        load_in_4bit=args.load_in_4bit,
        batch_size=args.batch_size,
        limit=args.limit,
    )

    print("Susu Books extraction benchmark")
    print(f"  Examples                 : {metrics['examples']}")
    print(f"  Parse rate               : {metrics['parse_rate'] * 100:.1f}%")
    print(f"  Function name accuracy   : {metrics['function_name_accuracy'] * 100:.1f}%")
    print(f"  Argument match accuracy  : {metrics['argument_match_accuracy'] * 100:.1f}%")
    print(f"  Exact match accuracy     : {metrics['exact_match_accuracy'] * 100:.1f}%")
    print("  Per language:")
    for language, score in metrics["per_language_argument_match"].items():
        print(f"    {language:>4} : {score * 100:.1f}%")
    print("  Per intent:")
    for intent, score in metrics["per_intent_argument_match"].items():
        print(f"    {intent:>15} : {score * 100:.1f}%")

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        print(f"  Metrics JSON             : {args.output_json}")


if __name__ == "__main__":
    main()
