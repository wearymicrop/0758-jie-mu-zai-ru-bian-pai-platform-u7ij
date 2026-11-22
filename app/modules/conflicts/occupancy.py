from collections import Counter, defaultdict
from itertools import combinations

from app.modules.calendars.intervals import overlaps


def audit_holds(calendar):
    present = {"stage": calendar["stages"], "tech": calendar["technicians"]}
    counts = Counter(hold["id"] for hold in calendar["holds"])
    entries = defaultdict(list)
    issues = []
    for line, hold in enumerate(calendar["holds"], 1):
        item = {**hold, "source_index": line}
        if counts[hold["id"]] > 1 or hold["resource"] not in present[hold["type"]] or hold["start"] >= hold["end"]:
            issues.append({**item, "code": "INVALID_HOLD"})
            continue
        entries[f'{hold["type"]}:{hold["resource"]}'].append(item)
    clashes = [{"resource": key, "left": a["id"], "right": b["id"],
                "start": max(a["start"], b["start"]), "end": min(a["end"], b["end"])}
               for key, holds in sorted(entries.items()) for a,b in combinations(holds, 2)
               if overlaps((a["start"], a["end"]), (b["start"], b["end"]))]
    return {"holds": dict(entries), "issues": issues, "overlaps": clashes}


def blockers(holds, start, end):
    return [h for h in holds if overlaps((h["start"], h["end"]), (start, end))]
