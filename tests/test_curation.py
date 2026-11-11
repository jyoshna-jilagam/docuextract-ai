import json

from curation.quality_checks import check_sample
from data_generation.generate_invoices import PROMPT, add_noise, to_row, build_label, render
import random


def make_row(seed):
    rng = random.Random(seed)
    label, defects = build_label(rng)
    return to_row("x", render(rng, label), label, {"defects": defects}), rng


def test_clean_rows_pass_gate():
    for seed in range(50):
        row, _ = make_row(seed)
        assert check_sample(row["instruction"], row["output"]) == []


def test_corrupted_rows_fail_gate():
    for seed in range(50):
        row, rng = make_row(seed)
        noisy = add_noise(rng, row)
        assert check_sample(noisy["instruction"], noisy["output"]) != []


def test_invalid_json_rejected():
    assert check_sample(PROMPT + "doc", "{not json") == ["invalid_json"]
