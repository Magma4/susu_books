# Susu Books Gemma 4 LoRA Training Results

Date: May 16, 2026

This run fine-tuned a Gemma 4 instruction model for multilingual transaction extraction. The model was trained to convert English, Twi, Hausa, Nigerian Pidgin, and Swahili trade utterances into structured tool-call style outputs for the Susu Books ledger backend.

## Kaggle Artifact

The trained adapter archive is intentionally not stored in Git because it is a large binary artifact.

- Local archive: `susu-books-lora-kaggle.tar.gz`
- Local size: 391 MB
- SHA-256: `8b64c3ba9f81f6f0897b156e4f4a3bb03f6036341cb852ec787bec83d331ca34`
- Archive contents include: `adapter_model.safetensors`, `adapter_config.json`, tokenizer/processor files, `training_summary.json`, and training checkpoints.

## Run Summary

- Base model: `unsloth/gemma-4-e2b-it`
- Training examples: 2,700
- Validation examples: 300
- Epochs: 1
- Effective batch size: 8
- Train loss: 0.0753
- Runtime: 3,899.55 seconds
- Peak VRAM: 12.95 GB
- Kaggle output directory: `/kaggle/working/susu-books-lora`

## Submission Note

For the hackathon writeup, describe this as an extraction-focused LoRA adapter. The fine-tune improves Gemma 4's ability to map multilingual informal-market utterances into reliable structured function calls. User-facing multilingual text remains handled by verified response templates, not free-form generation.
