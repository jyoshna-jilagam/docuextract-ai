import re
from decimal import Decimal

GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z0-9]$")
TOLERANCE = Decimal("0.01")
OPTIONAL_TEXT = ("supplier_address", "supplier_gstin", "customer_gstin", "due_date", "invoice_number")


def _d(value):
    return None if value is None else Decimal(str(value))


def missing_fields(inv):
    names = [k for k in OPTIONAL_TEXT if inv.get(k) is None]
    names += [f"items[{i}].hsn_sac" for i, it in enumerate(inv.get("items") or []) if it.get("hsn_sac") is None]
    return names


def check(inv):
    errors = []
    for key in ("supplier_gstin", "customer_gstin"):
        value = inv.get(key)
        if value is not None and not GSTIN_RE.match(value):
            errors.append(f"{key}_invalid_format")
    items = inv.get("items") or []
    for i, it in enumerate(items):
        qty, price, amount = _d(it.get("quantity")), _d(it.get("unit_price")), _d(it.get("taxable_amount"))
        if None not in (qty, price, amount) and abs(qty * price - amount) > TOLERANCE:
            errors.append(f"item_{i}_amount_mismatch")
    amounts = [_d(it.get("taxable_amount")) for it in items]
    subtotal = _d(inv.get("subtotal"))
    if subtotal is not None and amounts and None not in amounts and abs(sum(amounts) - subtotal) > TOLERANCE:
        errors.append("subtotal_mismatch")
    parts = [_d(inv.get(k)) for k in ("cgst", "sgst", "igst")]
    tax = _d(inv.get("total_tax"))
    if tax is not None and any(p is not None for p in parts):
        if abs(sum(p for p in parts if p is not None) - tax) > TOLERANCE:
            errors.append("total_tax_mismatch")
    total = _d(inv.get("grand_total"))
    if None not in (subtotal, tax, total) and abs(subtotal + tax - total) > TOLERANCE:
        errors.append("grand_total_mismatch")
    return errors
