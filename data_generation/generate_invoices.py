import argparse
import json
import random
import re
import string
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from data_generation.dataset_split import split_ids, write_split_info
from validation.consistency_checker import check, missing_fields

PROMPT = (
    "Extract the invoice fields from the document below and return only JSON that follows the invoice schema. "
    "Use null for any value that is not present. Do not guess. List null fields in missing_fields and "
    "arithmetic or format problems in validation_errors.\n\nDocument:\n"
)
DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%Y-%m-%d", "%d.%m.%y", "%d %B %Y"]
STATES = {"29": "Karnataka", "27": "Maharashtra", "33": "Tamil Nadu", "36": "Telangana",
          "37": "Andhra Pradesh", "07": "Delhi", "24": "Gujarat", "19": "West Bengal"}
CITIES = {"29": ["Bengaluru", "Mysuru"], "27": ["Pune", "Nagpur"], "33": ["Chennai", "Coimbatore"],
          "36": ["Hyderabad", "Warangal"], "37": ["Visakhapatnam", "Vijayawada"], "07": ["New Delhi"],
          "24": ["Surat", "Vadodara"], "19": ["Kolkata"]}
FIRST = ["Sri", "Lakshmi", "Balaji", "Veera", "Annapurna", "Sai", "Kaveri", "Surya", "Ganga", "Deccan",
         "Konark", "Ashoka", "Vindhya", "Nila", "Orion", "Mahi"]
SECOND = ["Textiles", "Agro", "Electricals", "Stationery", "Hardware", "Foods", "Logistics", "Packaging",
          "Infotech", "Chemicals", "Plastics", "Machinery"]
SUFFIX = ["Traders", "Enterprises", "Industries", "Agencies", "Pvt Ltd", "LLP"]
STREETS = ["MG Road", "Station Road", "Gandhi Nagar", "Industrial Estate", "Market Street", "Temple Road", "Ring Road"]
PRODUCTS = [
    ("Office Paper A4 Ream", "4802", 180, 420, 12), ("Steel Bolts M10", "7318", 2, 15, 18),
    ("LED Bulb 9W", "8539", 60, 150, 12), ("Cotton Fabric Roll", "5208", 900, 3500, 5),
    ("Plastic Crates", "3923", 150, 600, 18), ("Packaged Rice 25kg", "1006", 900, 1800, 5),
    ("Laptop Bag", "4202", 450, 1500, 18), ("Copper Wire 1.5mm", "8544", 1200, 4800, 18),
    ("Printer Toner Cartridge", "8443", 1800, 6500, 18), ("Transport Service", "996511", 2500, 15000, 5),
    ("IT Support Service", "998313", 5000, 40000, 18), ("Machine Maintenance", "998719", 3000, 25000, 18),
]


def q2(x):
    return Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP)


def flt(x):
    return None if x is None else float(x)


def indian(v):
    whole, frac = f"{v:.2f}".split(".")
    if len(whole) > 3:
        head, tail, parts = whole[:-3], whole[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        whole = ",".join(([head] if head else []) + parts + [tail])
    return f"{whole}.{frac}"


def make_gstin(rng, code):
    pan = "".join(rng.choices(string.ascii_uppercase, k=5)) + f"{rng.randint(0, 9999):04d}" + rng.choice(string.ascii_uppercase)
    return f"{code}{pan}{rng.randint(1, 9)}Z{rng.choice(string.ascii_uppercase + string.digits)}"


def make_company(rng, code):
    name = f"{rng.choice(FIRST)} {rng.choice(SECOND)} {rng.choice(SUFFIX)}"
    addr = f"{rng.randint(1, 320)}, {rng.choice(STREETS)}, {rng.choice(CITIES[code])}, {STATES[code]} {rng.randint(500000, 799999)}"
    return name, addr


def build_label(rng):
    sc = rng.choice(list(STATES))
    inter = rng.random() < 0.35
    cc = rng.choice([c for c in STATES if c != sc]) if inter else sc
    sname, saddr = make_company(rng, sc)
    cname, _ = make_company(rng, cc)
    structure = rng.choices(["gst", "exempt", "no_tax"], [0.84, 0.06, 0.10])[0]
    prods = rng.sample(PRODUCTS, rng.randint(1, 3))
    rate = Decimal(prods[0][4]) if structure == "gst" else Decimal(0)
    items = []
    for desc, hsn, lo, hi, _ in prods:
        qty, price = rng.randint(1, 60), q2(rng.uniform(lo, hi))
        items.append({"description": desc, "hsn_sac": hsn, "quantity": qty,
                      "unit_price": float(price), "taxable_amount": float(q2(qty * price))})
    subtotal = sum(Decimal(str(i["taxable_amount"])) for i in items)
    tax = q2(subtotal * rate / 100)
    cgst = sgst = igst = None
    if structure == "gst":
        if inter:
            igst = tax
        else:
            cgst = q2(tax / 2)
            sgst = tax - cgst
    total_tax = None if structure == "no_tax" else tax
    grand = subtotal + (total_tax or 0)
    start = date(2025, 4, 1) + timedelta(days=rng.randint(0, 570))
    label = {
        "supplier_name": sname, "supplier_address": saddr, "supplier_gstin": make_gstin(rng, sc),
        "customer_name": cname, "customer_gstin": make_gstin(rng, cc),
        "invoice_number": rng.choice([f"INV-{rng.randint(1000, 99999)}", f"TI/25-26/{rng.randint(1, 9999):04d}", f"SB{rng.randint(100, 9999)}"]),
        "invoice_date": start.isoformat(), "due_date": (start + timedelta(days=rng.choice([15, 30, 45]))).isoformat(),
        "currency": "INR", "items": items, "subtotal": flt(subtotal), "cgst": flt(cgst), "sgst": flt(sgst),
        "igst": flt(igst), "total_tax": flt(total_tax), "grand_total": flt(grand),
    }
    defects = [structure] + (["inter_state"] if inter else [])
    for key in OPTIONAL_KEYS:
        if rng.random() < 0.10:
            label[key] = None
            defects.append(f"missing_{key}")
    for it in items:
        if rng.random() < 0.10:
            it["hsn_sac"] = None
            if "missing_hsn_sac" not in defects:
                defects.append("missing_hsn_sac")
    for key in ("supplier_gstin", "customer_gstin"):
        if label[key] and rng.random() < 0.05:
            label[key] = label[key][:-1] if rng.random() < 0.5 else label[key].lower()
            defects.append("malformed_gstin")
    if rng.random() < 0.08:
        key = rng.choice(["grand_total", "total_tax", "subtotal"])
        if label[key] is not None:
            shift = rng.choice([10, 50, 100, 500])
            label[key] = round(label[key] + shift, 2) if rng.random() < 0.5 or label[key] <= shift else round(label[key] - shift, 2)
            defects.append("arithmetic_inconsistency")
    label["missing_fields"] = missing_fields(label)
    label["validation_errors"] = check(label)
    return label, defects


OPTIONAL_KEYS = ("supplier_address", "supplier_gstin", "customer_gstin", "due_date", "invoice_number")


def ln(prefix, value):
    return None if value is None else f"{prefix}{value}"


def render(rng, L):
    style = rng.choice(["indian", "western", "plain", "rs", "inr"])
    date_fmt = rng.choice(DATE_FORMATS)
    placeholder = rng.choice([None, "N/A", "-", "Not provided"])

    def m(v):
        if v is None:
            return None
        return {"indian": indian(v), "western": f"{v:,.2f}", "plain": f"{v:.2f}",
                "rs": f"Rs. {indian(v)}", "inr": f"{indian(v)} INR"}[style]

    def s(v):
        return placeholder if v is None else v

    def dt(v):
        return None if v is None else date.fromisoformat(v).strftime(date_fmt)

    tax = [ln(f"{n}: ", m(L[k])) for k, n in (("cgst", "CGST"), ("sgst", "SGST"), ("igst", "IGST"), ("total_tax", "Total Tax"))]
    layout = rng.choice(["table", "compact", "letter"])
    if layout == "table":
        rows = [f"{i + 1} | {it['description']} | {s(it['hsn_sac']) or ''} | {it['quantity']} | {m(it['unit_price'])} | {m(it['taxable_amount'])}"
                for i, it in enumerate(L["items"])]
        lines = ["TAX INVOICE", L["supplier_name"], ln("Address: ", s(L["supplier_address"])), ln("GSTIN: ", s(L["supplier_gstin"])),
                 ln("Invoice No: ", s(L["invoice_number"])), ln("Date: ", dt(L["invoice_date"])), ln("Due Date: ", s(dt(L["due_date"]))),
                 f"Bill To: {L['customer_name']}", ln("Customer GSTIN: ", s(L["customer_gstin"])),
                 "Sl | Description | HSN/SAC | Qty | Rate | Amount"] + rows + [ln("Subtotal: ", m(L["subtotal"]))] + tax + [ln("Grand Total: ", m(L["grand_total"])), f"Currency: {rng.choice(['INR', 'Rs.'])}"]
    elif layout == "compact":
        items = "; ".join(f"{it['description']} (HSN {s(it['hsn_sac']) or '-'}) {it['quantity']} x {m(it['unit_price'])} = {m(it['taxable_amount'])}" for it in L["items"])
        lines = [f"Inv {s(L['invoice_number'])} dt {dt(L['invoice_date'])} due {s(dt(L['due_date']))}",
                 f"From {L['supplier_name']}, {s(L['supplier_address'])}, GSTIN {s(L['supplier_gstin'])}",
                 f"To {L['customer_name']}, GSTIN {s(L['customer_gstin'])}", f"Items: {items}",
                 " ".join(t for t in [ln("Sub ", m(L["subtotal"]))] + tax if t), ln("Total ", m(L["grand_total"]))]
    else:
        items = [f"- {it['description']}, HSN/SAC {s(it['hsn_sac']) or 'n/a'}, {it['quantity']} units at {m(it['unit_price'])}, amount {m(it['taxable_amount'])}" for it in L["items"]]
        lines = [f"Dear {L['customer_name']},", "", f"Please find invoice {s(L['invoice_number'])} dated {dt(L['invoice_date'])} for the supply of:"] + items + \
                [ln("Subtotal ", m(L["subtotal"]))] + tax + [ln("Amount payable ", m(L["grand_total"])), ln("Payment due by ", s(dt(L["due_date"]))),
                 "", "Regards,", L["supplier_name"], ln("", s(L["supplier_address"])), ln("GSTIN ", s(L["supplier_gstin"])),
                 ln("Your GSTIN on record: ", s(L["customer_gstin"]))]
    text = "\n".join(x for x in lines if x is not None)
    return text.upper() if rng.random() < 0.15 else text


def to_row(rec_id, document, label, meta):
    return {"id": rec_id, "instruction": PROMPT + document, "input": "",
            "output": json.dumps(label, ensure_ascii=False), "meta": meta}


def near_duplicate(rng, document):
    return rng.choice([document.upper(), document.replace("\n", "\n\n"), "\n".join(l + "  " for l in document.split("\n"))])


FAKE = {
    "supplier_gstin": lambda r: make_gstin(r, "29"),
    "customer_gstin": lambda r: make_gstin(r, "27"),
    "due_date": lambda r: (date(2026, 1, 1) + timedelta(days=r.randint(0, 200))).isoformat(),
    "supplier_address": lambda r: f"{r.randint(1, 99)}, Main Road, Chennai, Tamil Nadu 600001",
}


def add_noise(rng, row):
    label = json.loads(row["output"])
    kind = rng.choice(["hallucinated_value", "wrong_amount", "broken_json"])
    nulls = [k for k in FAKE if label[k] is None]
    if kind == "hallucinated_value" and not nulls:
        kind = "wrong_amount"
    if kind == "hallucinated_value":
        key = rng.choice(nulls)
        label[key] = FAKE[key](rng)
        label["missing_fields"] = missing_fields(label)
    elif kind == "wrong_amount":
        label["grand_total"] = round(label["grand_total"] * rng.uniform(1.05, 1.4), 2)
    out = json.dumps(label, ensure_ascii=False)
    if kind == "broken_json":
        out = out[: int(len(out) * rng.uniform(0.6, 0.9))]
    return {**row, "output": out, "meta": {**row["meta"], "label_noise": kind}}


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1800)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--noise_rate", type=float, default=0.10)
    ap.add_argument("--dup_rate", type=float, default=0.12)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    base, seen = {}, set()
    while len(base) < a.n:
        label, defects = build_label(rng)
        doc = render(rng, label)
        key = re.sub(r"\s+", " ", doc).casefold()
        if key in seen:
            continue
        seen.add(key)
        rid = f"inv{len(base):05d}"
        base[rid] = to_row(rid, doc, label, {"defects": defects})
    ids = split_ids(list(base), a.seed)
    rows = {"validation": [base[i] for i in ids["validation"]], "test": [base[i] for i in ids["test"]]}
    train = [base[i] for i in ids["train"]]
    noisy = {r["id"] for r in rng.sample(train, int(len(train) * a.noise_rate))}
    train_rows = [add_noise(rng, r) if r["id"] in noisy else r for r in train]
    for r in rng.sample(train, int(len(train) * a.dup_rate)):
        doc = r["instruction"][len(PROMPT):]
        exact = rng.random() < 0.5
        text = doc if exact else near_duplicate(rng, doc)
        src = next(t for t in train_rows if t["id"] == r["id"])
        train_rows.append({**src, "id": f"{r['id']}_{'dup' if exact else 'near'}", "instruction": PROMPT + text,
                           "meta": {**src["meta"], "duplicate_of": r["id"], "duplicate_kind": "exact" if exact else "near"}})
    rows["train"] = train_rows
    write_jsonl("data/raw/train_raw.jsonl", train_rows)
    write_jsonl("data/validation/validation.jsonl", rows["validation"])
    write_jsonl("data/test/test.jsonl", rows["test"])
    info = write_split_info("artifacts/reports/split_info.json", rows, a.seed)
    print(json.dumps(info["counts"]), "overlap:", info["normalized_document_overlap"])


if __name__ == "__main__":
    main()
