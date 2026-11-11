import json
import random

from data_generation.generate_invoices import build_label
from validation.consistency_checker import check, missing_fields
from validation.schema_validator import validate


def test_generated_labels_match_schema_and_checks():
    rng = random.Random(1)
    for _ in range(200):
        label, _ = build_label(rng)
        assert validate(label) == []
        assert label["validation_errors"] == check(label)
        assert label["missing_fields"] == missing_fields(label)


def test_checker_flags_wrong_total():
    label, _ = build_label(random.Random(3))
    label["grand_total"] = 1.0
    assert "grand_total_mismatch" in check(label)
