# -*- coding: utf-8 -*-
# Calculations for Costeo aggregates (server-side)

def _flt(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def calculate_all_aggregates(doc):
    """
    Server-side aggregation that preserves user-entered fields.
    We intentionally do NOT overwrite shipping_cost because it is user input.
    """
    productos = doc.get("costeo_producto") or []

    for row in productos:
        base = _flt(row.material_cost) + _flt(row.services_cost) + _flt(row.shipping_cost)
        overhead_pct = _flt(row.overhead_pct)
        row.overhead_amt = base * (overhead_pct / 100.0)
        row.total_unit_cost = base + _flt(row.overhead_amt)

        margin_pct = _flt(row.margin_pct) / 100.0
        if margin_pct > 0 and margin_pct < 1:
            row.unit_sales_price = row.total_unit_cost / (1 - margin_pct)

        if _flt(row.unit_sales_price) > 0:
            row.total_sales_price = _flt(row.unit_sales_price) * _flt(row.qty)
