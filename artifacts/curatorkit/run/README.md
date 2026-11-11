---
tags:
- curatorkit
configs:
- config_name: sft_alpaca
  default: true
  description: curatorkit sft_alpaca export, sha256 2a440ddb8bde57d9f6089812e568f37afc7de493bd9dac1bdca5edac2bb9610e
  data_files:
  - split: train
    path: sft_alpaca.jsonl
- config_name: sft_messages
  description: curatorkit sft_messages export, sha256 33026a2598f2f658e200fce2ed362051f2936c578c106121f945129e28daff90
  data_files:
  - split: train
    path: sft_messages.jsonl
---

# Dataset Card: docuextract_train

## Summary

- **Run timestamp**: 2026-11-11T04:32:34.442580Z
- **Wall clock time**: 46.4s
- **Pipeline config hash**: `165dc037766c562d`

## Source Documents

  - Unknown

## Pipeline Stages

| Step | Input | Passed | Recovered | Rejected | Forward |
|------|-------|--------|-----------|----------|---------|
| JSONLReader | 1270 | 1270 | — | 0 | 1270 |
| SchemaGate | 1270 | 1270 | 0 | 0 | 1270 |
| ExactDeduplicator | 1270 | 1158 | — | — | 1158 |
| MinHashDeduplicator | 1158 | 1134 | — | — | 1134 |
| TextCleaner | 1134 | 1134 | — | — | 1134 |
| AlpacaExporter | — | 1134 | — | — | 1134 |
| MessagesExporter | — | 1134 | — | — | 1134 |

## Gate Pass Rates and Rejection Breakdown

- **JSONLReader**: 1270/0 passed (N/A), 0 rejected
- **SchemaGate**: 1270/1270 passed (100.0%), 0 rejected


**Rejection reasons:**
  - None

## Deduplication

  - near_duplicates_removed: 24
  - surviving_count: 1134

## Known Limitations

- MinHash threshold used: **0.85** — this is a starting point, not a universal answer. Adjust per domain (legal, medical, and other domain-specific corpora may need a lower threshold to avoid losing structurally similar but semantically valid examples).
- Table extraction requires `extract_tables: true` on the PDF reader and MinerU with GPU support. Disabled by default.
- Token counting uses a whitespace tokenizer by default. For exact LLM context window
  enforcement, enable `use_tiktoken: true` in the SchemaGate config.
- Both within-run (MinHash/Diversity) and cross-run (EmbeddingDeduplicator) deduplication
  are available. Cross-run dedup persists an embedding index across runs; use
  `embedding_reset_index: true` to start fresh.

## Reproduction

```bash
pip install curatorkit
curatorkit run pipeline.yaml --output-dir ./out/
```

## Tool Versions

- **curatorkit**: 0.1.24
- **python**: 3.12.10

## Configs

Load one with `datasets.load_dataset("<this folder or Hub repo>", "<config>")`.

| Config | Splits (rows) | Columns |
|--------|---------------|---------|
| `sft_alpaca` | train (1134) | `instruction`: string<br>`input`: string (empty when there is no input)<br>`output`: string |
| `sft_messages` | train (1134) | `messages`: list of {role, content}; role is system, user or assistant |
