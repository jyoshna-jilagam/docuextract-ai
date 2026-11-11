import json
from collections import Counter
from pathlib import Path

from curation.curate_dataset import FINAL, RAW, REJECTED, RUN_DIR, read_jsonl

REPORTS = Path("artifacts/reports")
SPLIT_FILES = {"train": RAW, "validation": Path("data/validation/validation.jsonl"), "test": Path("data/test/test.jsonl")}


def defect_counts(rows):
    counter = Counter()
    for row in rows:
        counter.update(row["meta"]["defects"])
    return dict(sorted(counter.items()))


def main():
    splits = {name: read_jsonl(path) for name, path in SPLIT_FILES.items()}
    rejected = read_jsonl(REJECTED)
    curated = read_jsonl(FINAL)
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    raw = splits["train"]
    noisy = [r for r in raw if "label_noise" in r["meta"]]
    noisy_caught = [r for r in rejected if "label_noise" in r["meta"]]
    dup_rows = [r for r in raw if "duplicate_of" in r["meta"]]
    stages = manifest["stage_counts"]
    report = {
        "counts": {"raw_train": len(raw), "quality_gate_rejected": len(rejected),
                   "after_exact_dedup": stages["ExactDeduplicator"]["output_count"],
                   "after_minhash_dedup": stages["MinHashDeduplicator"]["output_count"],
                   "curated_train": len(curated), "validation": len(splits["validation"]), "test": len(splits["test"])},
        "injected_label_noise": {"total": len(noisy), "caught_by_quality_gate": len(noisy_caught),
                                 "by_type": dict(Counter(r["meta"]["label_noise"] for r in noisy))},
        "injected_duplicates": {"total": len(dup_rows), "by_kind": dict(Counter(r["meta"]["duplicate_kind"] for r in dup_rows))},
        "quality_gate_rejection_reasons": dict(Counter(x.split(":")[0] for r in rejected for x in r["reasons"])),
        "defect_counts_by_split": {name: defect_counts(rows) for name, rows in splits.items()},
        "curatorkit_artifacts": str(RUN_DIR),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    c, n, d = report["counts"], report["injected_label_noise"], report["injected_duplicates"]
    card = f"""# Dataset Card: DocuExtract Synthetic GST Invoices

## Summary
Fully synthetic invoice documents with fictional businesses and GSTIN-like identifiers, paired with ground-truth JSON labels
that follow `config/extraction_schema.json`. Task: structured extraction with null for absent fields.

## Splits (created before curation, by base invoice id)
| Split | Rows |
|---|---|
| train_raw | {c['raw_train']} |
| train_curated | {c['curated_train']} |
| validation | {c['validation']} |
| test | {c['test']} |

Normalized-document overlap between splits is verified to be zero (see `artifacts/reports/split_info.json`).
Validation and test never pass through curation and contain no injected noise or duplicates.

## Curation (train only)
1. Quality gate: JSON validity, schema validity, grounding of every non-null value in the document, recomputed arithmetic and missing-field checks.
2. CuratorKIT: schema gate, exact deduplication, MinHash near-duplicate removal (threshold 0.85), text cleaning, Alpaca and chat exports.

| Stage | Rows |
|---|---|
| Raw train | {c['raw_train']} |
| After quality gate | {c['raw_train'] - c['quality_gate_rejected']} |
| After exact dedup | {c['after_exact_dedup']} |
| After MinHash dedup | {c['after_minhash_dedup']} |

Deliberately injected into train_raw: {n['total']} corrupted labels ({n['by_type']}), of which the quality gate rejected {n['caught_by_quality_gate']};
{d['total']} duplicates ({d['by_kind']}).

## Intended use and limits
- Used to compare base, raw-fine-tuned and curated-fine-tuned models under identical evaluation.
- Label noise is injected by the generator, so the benefit of curation on this data is a controlled-experiment result, not a real-world claim.
- All performance numbers on this data describe synthetic documents only. Real-world accuracy is not claimed.
- Dates in numeric formats are labelled with the Indian day-month-year convention.
- Names, addresses and GSTINs are random and fictional; GSTIN check digits are not validated and any resemblance to real entities is coincidental.
- Public datasets (for example receipts or invoices with permissive licences) are not bundled; check each licence before adding any.
"""
    (REPORTS / "DATASET_CARD.md").write_text(card, encoding="utf-8")
    print(json.dumps(report["counts"]), report["injected_label_noise"]["caught_by_quality_gate"], "of", n["total"])


if __name__ == "__main__":
    main()
