from collections import defaultdict

from app.modules.conflicts.inspection import invalid_resources
from app.modules.schedule.search import search


def plan(orders, dependencies, calendar, conflicts):
    blocked = {**conflicts["order_issues"], **dependencies["issues"]}
    indexed = {item["id"]: item for item in orders}
    holds = defaultdict(list, {key: list(rows) for key, rows in conflicts["holds"].items()})
    uncertain = invalid_resources(conflicts)
    states = {key: {**indexed[key], **issue, "status": "isolated"} for key, issue in blocked.items()}
    for key in dependencies["order"]:
        if key in blocked:
            continue
        job = indexed[key]
        parents = [states[parent] for parent in job["needs"]]
        missing = [parent["id"] for parent in parents if parent["status"] != "scheduled"]
        if missing:
            states[key] = {**job, "status": "pending", "code": "DEPENDENCY_BLOCKED", "related": missing}
            continue
        release = max([job["release"], *(parent["end"] for parent in parents)])
        slot, code, related = search(job, calendar, holds, release, uncertain)
        state = {**job, "status": "pending", "code": code, "related": related, "ready": release}
        if slot:
            start, tech = slot
            end = start + job["duration"]
            stage_end = end + job["reset"]
            state.update(status="scheduled", start=start, end=end, tech=tech, stage_end=stage_end)
            holds['stage:' + job["stage"]].append({"id": key, "start": start, "end": stage_end})
            holds['tech:' + tech].append({"id": key, "start": start, "end": end})
        states[key] = state
    return {"jobs": [states[key] for key in sorted(states)]}
