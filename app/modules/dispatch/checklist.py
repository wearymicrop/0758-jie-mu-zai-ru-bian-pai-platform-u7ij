from collections import defaultdict


def build(schedule, calendar):
    groups = defaultdict(list)
    deferred = []
    for job in schedule["jobs"]:
        if job["status"] != "scheduled":
            deferred.append({k: job[k] for k in ("id", "line", "status", "code", "related")})
            continue
        groups[job["stage"]].append({
            **{k: job[k] for k in ("id", "show", "title", "line", "start", "end", "stage_end", "tech", "needs")},
            "technician": calendar["technicians"][job["tech"]]["name"],
        })
    return {"date": calendar["date"], "stages": [{"stage": stage, "steps": sorted(rows, key=lambda row: row["start"])}
                                                   for stage, rows in sorted(groups.items())], "deferred": deferred}
