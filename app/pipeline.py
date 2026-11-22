from app.modules.calendars.registry import load
from app.modules.conflicts.inspection import order_issues
from app.modules.conflicts.occupancy import audit_holds
from app.modules.dependencies.checks import inspect
from app.modules.dispatch.checklist import build
from app.modules.orders.intake import collect
from app.modules.reconcile.audit import reconcile
from app.modules.schedule.planner import plan


def process(source):
    orders = collect(source["orders"])
    calendar = load(source["calendar"])
    dependencies = inspect(orders["orders"])
    conflicts = audit_holds(calendar)
    conflicts["order_issues"] = order_issues(orders["orders"], calendar)
    schedule = plan(orders["orders"], dependencies, calendar, conflicts)
    return {"orders": orders, "dependencies": dependencies, "calendars": calendar, "conflicts": conflicts,
            "schedule": schedule, "reconcile": reconcile(orders, schedule, conflicts),
            "dispatch": build(schedule, calendar)}
