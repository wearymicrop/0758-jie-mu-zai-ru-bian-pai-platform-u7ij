from app.modules.calendars.registry import choices
from app.modules.conflicts.occupancy import blockers


def search(order, calendar, holds, earliest, excluded):
    stage_key = 'stage:' + order["stage"]
    crew = choices(calendar, order["role"])
    best = []
    seen = set()
    duration, reset = order["duration"], order["reset"]
    has_window = False
    if stage_key in excluded:
        return None, "HOLD_UNCERTAIN", [stage_key]
    for tech in crew:
        tech_key = 'tech:' + tech
        if tech_key in excluded:
            seen.add(tech_key)
            continue
        skipped = set()
        for a, b in calendar["effective_stages"][order["stage"]]:
            for c, d in calendar["effective_tech"][tech]:
                start = max(a, c, earliest)
                latest = min(b - duration - reset, d - duration)
                while start <= latest:
                    has_window = True
                    blocking = (blockers(holds.get(stage_key, []), start, start + duration + reset)
                                + blockers(holds.get(tech_key, []), start, start + duration))
                    if not blocking:
                        best.append((start, tech, sorted(skipped)))
                        break
                    start = max(row["end"] for row in blocking)
                    skipped.update(row["id"] for row in blocking)
                    seen.update(skipped)
    if best:
        start, tech, trace = min(best)
        return (start, tech), "PLACED", trace
    reason = "RESOURCE_FULL" if has_window else "NO_WINDOW"
    if any('tech:' + tech in excluded for tech in crew):
        reason = "HOLD_UNCERTAIN"
    if not seen:
        seen = {stage_key, *('tech:' + tech for tech in crew)}
    return None, reason, sorted(seen)
