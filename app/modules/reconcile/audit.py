from collections import Counter
from itertools import combinations

from app.modules.calendars.intervals import overlaps
from app.modules.conflicts.occupancy import blockers


def reconcile(intake, schedule, conflicts):
    jobs = schedule["jobs"]
    placed = [job for job in jobs if job["status"] == "scheduled"]
    by_id = {job["id"]: job for job in jobs}
    counts = Counter(job["status"] for job in jobs)
    late = [{"id": job["id"], "line": job["line"], "minutes": job["end"] - job["deadline"]}
            for job in placed if job["end"] > job["deadline"]]
    collisions = []
    for a, b in combinations(placed, 2):
        if a["stage"] == b["stage"] and overlaps((a["start"], a["stage_end"]), (b["start"], b["stage_end"])):
            collisions.append([a["id"], b["id"], "stage"])
        if a["tech"] == b["tech"] and overlaps((a["start"], a["end"]), (b["start"], b["end"])):
            collisions.append([a["id"], b["id"], "tech"])
    premature = []
    for job in placed:
        for kind, key, end in (("stage", job["stage"], job["stage_end"]), ("tech", job["tech"], job["end"])):
            for hold in blockers(conflicts["holds"].get(f"{kind}:{key}", []), job["start"], end):
                collisions.append([job["id"], hold["id"], kind])
        for parent in job["needs"]:
            row = by_id.get(parent, {})
            if row.get("status") != "scheduled" or row["end"] > job["start"]:
                premature.append([job["id"], parent])
    totals = intake["counts"]
    row_gap = totals["input"] - len(jobs) - totals["isolated"] - totals["duplicates"] - totals["empty"]
    missing = sorted({order["id"] for order in intake["orders"]} ^ by_id.keys())
    balanced = not (row_gap or collisions or premature or missing or len(jobs) != len(by_id))
    return {"status": "MATCHED" if balanced else "MISMATCH", "row_gap": row_gap,
            "scheduled": counts["scheduled"], "pending": counts["pending"], "isolated": counts["isolated"],
            "late_count": len(late), "late": late, "collisions": collisions, "premature": premature,
            "missing": missing, "source_issues": totals["isolated"], "hold_clashes": len(conflicts["overlaps"])}
