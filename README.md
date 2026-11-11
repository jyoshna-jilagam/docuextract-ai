# DocuExtract AI

Structured extraction from Indian GST invoices with a fine-tuned open-weight model, built for the Lexsi AI Safety and Alignment Hackathon (Track 1, Problem 5: Structured Output and Extraction).

This repository currently contains the data layer: a synthetic invoice generator, leak-free splits, and a quality-gated curation pipeline built on CuratorKIT.

## Problem

Small businesses handle many invoices and purchase orders. General LLMs often return invalid JSON, invent values for fields that are absent, or silently fix wrong totals. The goal is a model that returns schema-valid JSON, uses null for absent values, and flags inconsistent totals instead of correcting them.

## Status

| Component | State |
|---|---|
| Synthetic dataset generator and splits | Done |
| CuratorKIT curation and reports | Done |
| Schema validation and arithmetic checks | Done |
| Unit tests | Done |
| AlignTune fine-tuning (base, raw, curated) | Pending |
| AuditKIT evaluation | Pending |
| Streamlit dashboard | Pending |

No model metrics are reported yet. Nothing in this repository claims model accuracy.

## Pipeline

```
generate base invoices -> split by invoice id (train / validation / test)
        -> add duplicates and label noise to train only -> train_raw.jsonl
        -> quality gate -> CuratorKIT (schema gate, exact dedup, MinHash dedup, clean, export)
        -> train_curated.jsonl
validation.jsonl and test.jsonl never enter curation.
```

## Dataset design

Each sample is a fictional invoice document plus a ground-truth JSON label (`config/extraction_schema.json`).

- Tax structures: CGST plus SGST, IGST, exempt, and no tax shown.
- Layouts: table, compact single line, letter style, with some uppercase variants.
- Number formats: Indian grouping (1,25,000.00), Western grouping, plain, Rs. prefix, INR suffix.
- Date formats: six styles, including ambiguous day-month values labelled with the day-month-year convention.
- Defects: missing GSTIN, due date, address, invoice number and HSN, malformed GSTIN, arithmetic inconsistency.
- Inconsistent totals are labelled as printed, with the problem listed in `validation_errors`. They are never corrected.
- Train only: exact and near duplicates, and deliberately corrupted labels (hallucinated value, wrong amount, broken JSON).

The corrupted labels are injected so that the effect of curation can be measured in a controlled way. They are not a claim about real-world label noise.

## Results of the data pipeline

| Stage | Rows |
|---|---|
| Raw train | 1,411 |
| After quality gate | 1,270 |
| After exact dedup | 1,158 |
| After MinHash dedup | 1,134 |
| Validation | 270 |
| Test | 270 |

The quality gate rejected all 141 injected corrupted labels and none of the clean ones. Split overlap is zero (`artifacts/reports/split_info.json`). Full statistics are in `artifacts/reports/quality_report.json` and `artifacts/reports/DATASET_CARD.md`.

## Quality gate

For each training sample the gate checks that the output is valid JSON, matches the schema, has every non-null value present in the document text, has `validation_errors` equal to the recomputed arithmetic and format checks, and has `missing_fields` equal to the null fields. CuratorKIT then applies its schema gate, exact and MinHash deduplication, and text cleaning, and writes the manifest, rejected samples, provenance and checksums to `artifacts/curatorkit/run/`.

## Setup and run

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m data_generation.generate_invoices --n 1800 --seed 42
python -m curation.curate_dataset
python -m curation.dataset_report
python -m pytest -q
```

Curation takes about 30 seconds because of MinHash deduplication.

## Outputs

| File | Purpose |
|---|---|
| `data/raw/train_raw.jsonl` | Training data before curation |
| `data/curated/train_curated.jsonl` | Curated training data, Alpaca format |
| `data/curated/train_curated_messages.jsonl` | Curated training data, chat format |
| `data/validation/validation.jsonl`, `data/test/test.jsonl` | Held-out sets, ground truth in `output` |
| `artifacts/reports/` | Dataset card, quality report, split info, rejected samples |
| `artifacts/curatorkit/run/` | CuratorKIT manifest, provenance and checksums |

## Project layout

```
config/            extraction schema
data_generation/   invoice generator and splitting
curation/          quality gate, CuratorKIT run, reports
validation/        schema validator and arithmetic checker
tests/             unit tests
```

## Limitations

- All data is synthetic. Results on it do not predict accuracy on real invoices.
- Text-only documents. Scanned images and layout are out of scope.
- GSTIN values are random and their check digits are not validated.
- Passing schema validation does not mean an invoice is tax compliant.
- No public invoice dataset is bundled. Add one only after checking its licence.
