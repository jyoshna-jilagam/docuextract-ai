import hashlib
import json
import random
import re
from pathlib import Path


def split_ids(ids, seed, ratios=(0.70, 0.15, 0.15)):
    ids = sorted(ids)
    random.Random(seed).shuffle(ids)
    a = int(len(ids) * ratios[0])
    b = a + int(len(ids) * ratios[1])
    return {"train": ids[:a], "validation": ids[a:b], "test": ids[b:]}


def normalize(text):
    return re.sub(r"\s+", " ", text).casefold()


def write_split_info(path, rows_by_split, seed):
    docs = {name: {normalize(r["instruction"]) for r in rows} for name, rows in rows_by_split.items()}
    overlap = {
        "train_vs_validation": len(docs["train"] & docs["validation"]),
        "train_vs_test": len(docs["train"] & docs["test"]),
        "validation_vs_test": len(docs["validation"] & docs["test"]),
    }
    info = {
        "seed": seed,
        "split_unit": "base invoice id; duplicates stay in train only",
        "counts": {name: len(rows) for name, rows in rows_by_split.items()},
        "id_checksums": {
            name: hashlib.sha256("\n".join(sorted(r["id"] for r in rows)).encode()).hexdigest()
            for name, rows in rows_by_split.items()
        },
        "normalized_document_overlap": overlap,
    }
    assert sum(overlap.values()) == 0, f"split leakage detected: {overlap}"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info
