from collections import defaultdict


def build_recovery_checklist(recovery, calendar):
    groups = defaultdict(list)
    deferred = []
    for job in recovery["jobs"]:
        if job["status"] != "scheduled":
            deferred.append({k: job[k] for k in ("id", "line", "status", "code", "related",
                                                 "entry_status", "recovery_status")})
            continue
        groups[job["stage"]].append({
            **{k: job[k] for k in ("id", "show", "title", "line", "start", "end", "stage_end",
                                   "tech", "needs", "entry_status", "recovery_status", "relocated",
                                   "original_stage", "original_start", "late_minutes")},
            "technician": calendar["technicians"][job["tech"]]["name"],
        })
    return {
        "closure_id": recovery["event"]["id"],
        "date": calendar["date"],
        "stages": [{"stage": stage, "steps": sorted(rows, key=lambda row: row["start"])}
                   for stage, rows in sorted(groups.items())],
        "deferred": deferred,
        "gaps": recovery["gaps"],
        "late": recovery["late"],
        "summary": recovery["summary"],
    }
