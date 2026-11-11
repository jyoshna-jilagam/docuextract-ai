import json
from pathlib import Path

import pytest

FILES = {n: Path(f"data/{d}/{f}") for n, d, f in [("train", "raw", "train_raw.jsonl"), ("val", "validation", "validation.jsonl"), ("test", "test", "test.jsonl")]}


@pytest.mark.skipif(not all(p.exists() for p in FILES.values()), reason="dataset not generated")
def test_no_id_overlap():
    ids = {n: {json.loads(l)["id"].split("_")[0] for l in p.read_text(encoding="utf-8").splitlines() if l} for n, p in FILES.items()}
    assert not ids["train"] & ids["val"] and not ids["train"] & ids["test"] and not ids["val"] & ids["test"]
