#!/usr/bin/env python3
"""
Susu Books - Ghana-NLP Dataset Importer
Imports the TWI_ENGLISH_PARALLEL_TEXT dataset from Hugging Face,
filters for transactional sentences, and formats them for SFT fine-tuning.
"""

import json
import argparse
from pathlib import Path
import os
import sys
import re

CURRENT_DIR = Path(__file__).resolve().parent


def resolve_repo_root() -> Path:
    """Find the folder containing backend/ai_contract.py in repo or Kaggle bundle layouts."""
    for candidate in (CURRENT_DIR, *CURRENT_DIR.parents, Path("/kaggle/working")):
        if (candidate / "backend" / "ai_contract.py").exists():
            return candidate
    if CURRENT_DIR.name == "training":
        return CURRENT_DIR.parent
    return CURRENT_DIR


REPO_ROOT = resolve_repo_root()

BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai_contract import EXTRACTION_SYSTEM_PROMPT

try:
    from datasets import load_dataset
except ImportError:
    print("Error: 'datasets' library not found. Run 'pip install datasets' first.")
    sys.exit(1)

# Keywords to filter English labels for business/market relevance
KEYWORDS = [
    r"\bbuy\b", r"\bsell\b", r"\bsold\b", r"\bbought\b", r"\bprice\b", r"\bcost\b",
    r"\bmoney\b", r"\bsika\b", r"\bcedi\b", r"\bnaira\b", r"\bshilling\b",
    r"\bmarket\b", r"\bstore\b", r"\bshop\b", r"\bstock\b", r"\binventory\b",
    r"\bprofit\b", r"\bloss\b", r"\bcheap\b", r"\bexpensive\b", r"\bpay\b",
    r"\bpaid\b", r"\breceipt\b", r"\bbusiness\b", r"\btrade\b", r"\btrader\b",
    r"\bcustomer\b", r"\bsupplier\b", r"\bloan\b", r"\borange\b", r"\brice\b",
    r"\btomato\b", r"\bonion\b", r"\byam\b", r"\bplantain\b", r"\bfish\b"
]

def format_tool_call(name, args):
    """Formats a tool call for SFT."""
    payload = {
        "name": name,
        "arguments": args
    }
    return f"<tool_call>\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}\n</tool_call>"

def map_to_tool(english_text):
    """
    Heuristically map English parallel text to a Susu Books tool call.
    This is a naive mapping to give the model 'general language debt' for specific intents.
    """
    text = english_text.lower()
    
    # Simple item extraction for variety (just basic ones)
    item = "unknown"
    for word in ["rice", "onions", "tomatoes", "plantain", "fish", "yams", "cassava"]:
        if word in text:
            item = word
            break

    if any(k in text for k in ["sell", "sold", "tɔn"]):
        return "record_sale", {"item": item, "quantity": 1, "sale_price": 0, "unit": "pieces"}
    
    if any(k in text for k in ["buy", "bought", "purchas", "tɔ"]):
        return "record_purchase", {"item": item, "quantity": 1, "unit_price": 0, "unit": "pieces"}
    
    if any(k in text for k in ["inventory", "stock", "stock level", "how much", "how many"]):
        return "check_inventory", {"item": item if item != "unknown" else ""}
    
    if any(k in text for k in ["summary", "business", "today", "report"]):
        return "daily_summary", {}
    
    # Fallback to clarify if we matched a keyword but no clear tool
    return "clarify_input", {"reason": "general_market_query"}

def main():
    parser = argparse.ArgumentParser(description="Import Ghana-NLP dataset for Susu Books.")
    parser.add_argument("--output", type=str, default="training/data/ghana_nlp_sft.jsonl", help="Output JSONL file path.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of processed examples.")
    args = parser.parse_args()

    print("Loading Ghana-NLP/TWI_ENGLISH_PARALLEL_TEXT from Hugging Face...")
    dataset = load_dataset("Ghana-NLP/TWI_ENGLISH_PARALLEL_TEXT", split="train")

    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    matches = 0
    total = 0
    
    keyword_regex = re.compile("|".join(KEYWORDS), re.IGNORECASE)

    with output_path.open("w", encoding="utf-8") as f:
        for i, row in enumerate(dataset):
            if args.limit and total >= args.limit:
                break
            
            twi_text = row.get("text", "").strip()
            english_label = row.get("label", "").strip()
            
            if not twi_text or not english_label:
                continue
                
            # Filter for transactional relevance
            if keyword_regex.search(english_label):
                tool_name, tool_args = map_to_tool(english_label)
                
                # Format for SFT
                sft_text = (
                    f"<start_of_turn>user\n{EXTRACTION_SYSTEM_PROMPT.strip()}\n\n{twi_text}<end_of_turn>\n"
                    f"<start_of_turn>model\n{format_tool_call(tool_name, tool_args)}<end_of_turn>"
                )
                
                record = {
                    "text": sft_text,
                    "_meta": {
                        "source": "ghana_nlp",
                        "original_english": english_label,
                        "mapped_tool": tool_name
                    }
                }
                
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                matches += 1
            
            total += 1
            if total % 1000 == 0:
                print(f"Processed {total} items, found {matches} matches...")

    print(f"\nDone! Saved {matches} transactional examples to {args.output}")

if __name__ == "__main__":
    main()
