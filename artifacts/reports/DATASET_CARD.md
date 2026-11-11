# Dataset Card: DocuExtract Synthetic GST Invoices

## Summary
Fully synthetic invoice documents with fictional businesses and GSTIN-like identifiers, paired with ground-truth JSON labels
that follow `config/extraction_schema.json`. Task: structured extraction with null for absent fields.

## Splits (created before curation, by base invoice id)
| Split | Rows |
|---|---|
| train_raw | 1411 |
| train_curated | 1134 |
| validation | 270 |
| test | 270 |

Normalized-document overlap between splits is verified to be zero (see `artifacts/reports/split_info.json`).
Validation and test never pass through curation and contain no injected noise or duplicates.

## Curation (train only)
1. Quality gate: JSON validity, schema validity, grounding of every non-null value in the document, recomputed arithmetic and missing-field checks.
2. CuratorKIT: schema gate, exact deduplication, MinHash near-duplicate removal (threshold 0.85), text cleaning, Alpaca and chat exports.

| Stage | Rows |
|---|---|
| Raw train | 1411 |
| After quality gate | 1270 |
| After exact dedup | 1158 |
| After MinHash dedup | 1134 |

Deliberately injected into train_raw: 141 corrupted labels ({'hallucinated_value': 19, 'wrong_amount': 79, 'broken_json': 43}), of which the quality gate rejected 141;
151 duplicates ({'exact': 84, 'near': 67}).

## Intended use and limits
- Used to compare base, raw-fine-tuned and curated-fine-tuned models under identical evaluation.
- Label noise is injected by the generator, so the benefit of curation on this data is a controlled-experiment result, not a real-world claim.
- All performance numbers on this data describe synthetic documents only. Real-world accuracy is not claimed.
- Dates in numeric formats are labelled with the Indian day-month-year convention.
- Names, addresses and GSTINs are random and fictional; GSTIN check digits are not validated and any resemblance to real entities is coincidental.
- Public datasets (for example receipts or invoices with permissive licences) are not bundled; check each licence before adding any.
