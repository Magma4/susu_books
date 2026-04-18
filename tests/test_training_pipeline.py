from __future__ import annotations

import unittest

from training.synthetic_data import build_split, format_for_sft


class SyntheticDataTests(unittest.TestCase):
    def test_build_split_balances_languages_and_contains_all_intents(self) -> None:
        examples = build_split(90, seed=42, split_name="train")
        self.assertEqual(len(examples), 90)

        by_language: dict[str, int] = {}
        by_intent: dict[str, int] = {}
        for example in examples:
            by_language[example.meta["language"]] = by_language.get(example.meta["language"], 0) + 1
            by_intent[example.meta["intent"]] = by_intent.get(example.meta["intent"], 0) + 1

        self.assertEqual(set(by_language.keys()), {"en", "tw", "ha", "pcm", "sw"})
        self.assertTrue(all(count == 18 for count in by_language.values()))
        self.assertIn("purchase", by_intent)
        self.assertIn("sale", by_intent)
        self.assertIn("expense", by_intent)
        self.assertIn("clarify", by_intent)

    def test_format_for_sft_emits_tool_call_markup(self) -> None:
        example = build_split(1, seed=7, split_name="train")[0]
        formatted = format_for_sft(example)
        self.assertIn("<start_of_turn>user", formatted["text"])
        self.assertIn("<start_of_turn>model", formatted["text"])
        self.assertIn("<tool_call>", formatted["text"])
        self.assertEqual(formatted["_meta"]["split"], "train")


if __name__ == "__main__":
    unittest.main()
