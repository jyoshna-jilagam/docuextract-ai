import re
from datetime import date
from decimal import Decimal

from data_generation.generate_invoices import DATE_FORMATS, PROMPT
from validation.consistency_checker import check, missing_fields
from validation.schema_validator import parse_and_validate

NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
TEXT_FIELDS = ("supplier_name", "supplier_address", "supplier_gstin", "customer_name", "customer_gstin", "invoice_number")
DATE_FIELDS = ("invoice_date", "due_date")
AMOUNT_FIELDS = ("subtotal", "cgst", "sgst", "igst", "total_tax", "grand_total")


def _norm(text):
    return re.sub(r"\s+", " ", text).casefold()


def _numbers(text):
    found = set()
    for token in NUMBER_RE.findall(text):
        found.add(Decimal(token.replace(",", "")))
    return found


def ungrounded_fields(document, label):
    text, numbers, bad = _norm(document), _numbers(document), []
    for key in TEXT_FIELDS:
        if label.get(key) is not None and _norm(label[key]) not in text:
            bad.append(key)
    for key in DATE_FIELDS:
        value = label.get(key)
        if value is None:
            continue
        try:
            forms = {_norm(date.fromisoformat(value).strftime(f)) for f in DATE_FORMATS}
        except ValueError:
            bad.append(key)
            continue
        if not any(form in text for form in forms):
            bad.append(key)
    for key in AMOUNT_FIELDS:
        if label.get(key) is not None and Decimal(str(label[key])) not in numbers:
            bad.append(key)
    for i, item in enumerate(label.get("items") or []):
        for key in ("description", "hsn_sac"):
            if item.get(key) is not None and _norm(item[key]) not in text:
                bad.append(f"items[{i}].{key}")
        for key in ("quantity", "unit_price", "taxable_amount"):
            if item.get(key) is not None and Decimal(str(item[key])) not in numbers:
                bad.append(f"items[{i}].{key}")
    return bad


def check_sample(instruction, output):
    label, schema_errors = parse_and_validate(output)
    if label is None:
        return ["invalid_json"]
    if schema_errors:
        return ["schema_violation"]
    document = instruction[len(PROMPT):] if instruction.startswith(PROMPT) else instruction
    reasons = [f"ungrounded:{k}" for k in ungrounded_fields(document, label)]
    if label["validation_errors"] != check(label):
        reasons.append("validation_errors_mismatch")
    if label["missing_fields"] != missing_fields(label):
        reasons.append("missing_fields_mismatch")
    return reasons
