from collections import defaultdict

from pydantic import ValidationError

from app.errors import DomainError
from app.manifest import canonical
from app.modules.orders.contract import WorkOrder
from app.sources import json_rows


def collect(text):
    groups = defaultdict(list)
    rows = []
    for line, raw, value, code in json_rows(text):
        if line > 400:
            raise DomainError("ORDER_LIMIT", "一个批次最多四百行工单")
        row = {"line": line, "raw": raw, "code": code}
        rows.append(row)
        if code:
            continue
        try:
            order = WorkOrder.model_validate(value).model_dump()
            if order["deadline"] <= order["release"]:
                raise ValueError("截止须晚于放行")
            order["needs"] = sorted(set(order["needs"]))
        except (ValidationError, ValueError) as exc:
            row.update(code="BAD_ORDER", detail=str(exc).splitlines()[0])
            continue
        row["id"] = order["id"]
        groups[order["id"]].append((row, order))

    orders = []
    for entries in groups.values():
        variants = {canonical(order) for _, order in entries}
        if len(variants) > 1:
            for row, _ in entries:
                row["code"] = "DUPLICATE_CONFLICT"
            continue
        first, order = entries[0]
        orders.append({**order, "line": first["line"]})
        first["code"] = "ACCEPTED"
        for row, _ in entries[1:]:
            row["code"] = "DUPLICATE_REPLAY"
    return {"rows": rows, "orders": orders, "counts": {
        "input": len(rows), "accepted": len(orders),
        "duplicates": sum(r["code"] == "DUPLICATE_REPLAY" for r in rows),
        "empty": sum(r["code"] == "EMPTY_ROW" for r in rows),
        "isolated": sum(r["code"] in {"BAD_JSON", "BAD_ORDER", "DUPLICATE_CONFLICT"} for r in rows),
    }}
