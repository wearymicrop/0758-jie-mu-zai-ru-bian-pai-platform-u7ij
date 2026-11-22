from app.modules.calendars.registry import choices


def order_issues(orders, calendar):
    issues = {}
    for order in orders:
        if order["stage"] not in calendar["stages"]:
            issues[order["id"]] = {"code": "UNKNOWN_STAGE", "related": [order["stage"]]}
        elif not choices(calendar, order["role"]):
            issues[order["id"]] = {"code": "UNKNOWN_ROLE", "related": [order["role"]]}
    return issues


def invalid_resources(conflicts):
    return {f'{row["type"]}:{row["resource"]}' for row in conflicts["issues"]}
