import json
import shutil
from pathlib import Path

from curatorkit import Curator, CuratorConfig

from curation.quality_checks import check_sample
from data_generation.generate_invoices import write_jsonl

RAW = Path("data/raw/train_raw.jsonl")
STAGE = Path("artifacts/curatorkit/stage_input.jsonl")
RUN_DIR = Path("artifacts/curatorkit/run")
REJECTED = Path("artifacts/reports/rejected_quality_gate.jsonl")
FINAL = Path("data/curated/train_curated.jsonl")


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    rows = read_jsonl(RAW)
    kept, rejected = [], []
    for row in rows:
        reasons = check_sample(row["instruction"], row["output"])
        (rejected if reasons else kept).append({**row, "reasons": reasons} if reasons else row)
    write_jsonl(REJECTED, rejected)
    write_jsonl(STAGE, [{"instruction": r["instruction"], "input": "", "output": r["output"]} for r in kept])
    if RUN_DIR.exists():
        shutil.rmtree(RUN_DIR)
    result = Curator(CuratorConfig(
        dataset=str(STAGE), format="alpaca", dedup="minhash", minhash_threshold=0.85, clean=True,
        min_tokens=10, max_tokens=4096, export_formats=["alpaca", "messages"],
        output_dir=str(RUN_DIR), name="docuextract_train",
    )).run()
    result.print_summary()
    FINAL.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(RUN_DIR / "sft_alpaca.jsonl", FINAL)
    shutil.copy(RUN_DIR / "sft_messages.jsonl", FINAL.with_name("train_curated_messages.jsonl"))
    print("quality gate kept", len(kept), "rejected", len(rejected))


if __name__ == "__main__":
    main()
