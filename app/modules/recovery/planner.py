from collections import defaultdict

from app.modules.calendars.intervals import overlaps
from app.modules.conflicts.inspection import invalid_resources
from app.modules.recovery.event import validate_event
from app.modules.schedule.search import search

CLOSURE_HOLD = "停场封场"


def _slot_key(candidate):
    slot, chosen_stage, _trace = candidate
    start, _tech = slot
    return start, 0 if chosen_stage is None else 1, chosen_stage or ""


def plan_recovery(result, event):
    """以原排程为基线，重算一次停场后的唯一执行单。

    已完工工序锁定为事实；开工中工序与尚未开工的工序参与重排；备用舞台
    仅在能给出更早开工位时才改场，同分裁决回到原工位。
    """
    calendar = result["calendars"]
    event = {"backup_stage": None, "as_of": event["start"], **event}
    validate_event(event, calendar)
    conflicts = result["conflicts"]
    excluded = invalid_resources(conflicts)
    holds = defaultdict(list, {key: list(rows) for key, rows in conflicts["holds"].items()})
    stage = event["stage"]
    stage_key = "stage:" + stage
    holds[stage_key].append({"id": CLOSURE_HOLD, "start": event["start"], "end": event["end"]})
    as_of = event["as_of"]

    jobs = {job["id"]: job for job in result["schedule"]["jobs"]}
    affected, replan_order, output = [], [], []

    for job in result["schedule"]["jobs"]:
        row = {**job, "original_stage": job["stage"], "original_start": job.get("start"),
               "original_end": job.get("end"), "entry_status": job["status"],
               "recovery_status": job["status"], "relocated": False, "late_minutes": 0}
        if job["status"] != "scheduled" or job["stage"] != stage:
            if job["status"] == "scheduled":
                _seed(holds, job)
            output.append(row)
            continue
        finished_before_inspection = job["stage_end"] <= as_of
        wholly_after_closure = job["start"] >= event["end"]
        if finished_before_inspection or wholly_after_closure:
            row["entry_status"] = row["recovery_status"] = "locked"
            _seed(holds, job)
            output.append(row)
            continue
        row["entry_status"] = "active" if job["start"] < as_of else "waiting"
        affected.append(row)
        replan_order.append(job["id"])

    by_id = {row["id"]: row for row in output + affected}
    for job_id in replan_order:
        row = by_id[job_id]
        job = jobs[job_id]
        parents = [by_id[parent] for parent in job["needs"] if parent in by_id]
        missing = [parent["id"] for parent in parents
                   if parent["recovery_status"] in {"pending", "isolated"} or not parent.get("end")]
        if missing:
            row.update(status="pending", code="DEPENDENCY_BLOCKED", related=missing,
                       recovery_status="waiting", start=None, end=None, stage_end=None, tech=None,
                       late_minutes=0)
            output.append(row)
            continue
        release = max([job["release"], as_of, *(parent["end"] for parent in parents)])
        candidates = []
        slot, code, related = search(job, calendar, holds, release, excluded)
        if slot:
            candidates.append((slot, None, related))
        if event["backup_stage"]:
            backup_slot, backup_code, backup_related = search(
                job, calendar, holds, release, excluded, stage_override=event["backup_stage"])
            if backup_slot:
                candidates.append((backup_slot, event["backup_stage"], backup_related))
            else:
                related = sorted(set(related) | set(backup_related))
                code = code if slot else backup_code
        if not candidates:
            row.update(status="pending", code=code, related=related, recovery_status="waiting",
                       start=None, end=None, stage_end=None, tech=None, late_minutes=0)
            output.append(row)
            continue
        (start, tech), chosen_stage, trace = min(candidates, key=_slot_key)
        end = start + job["duration"]
        stage_end = end + job["reset"]
        chosen = chosen_stage or stage
        row.update(status="scheduled", code="PLACED", related=trace, start=start, end=end,
                   stage_end=stage_end, tech=tech,
                   relocated=chosen != stage, late_minutes=max(0, end - job["deadline"]))
        if row["relocated"]:
            row["stage"] = chosen
            row["recovery_status"] = "relocated"
            holds["stage:" + chosen].append({"id": job["id"], "start": start, "end": stage_end})
        else:
            row["recovery_status"] = row["entry_status"]
            holds[stage_key].append({"id": job["id"], "start": start, "end": stage_end})
        holds["tech:" + tech].append({"id": job["id"], "start": start, "end": end})
        output.append(row)

    ordered = sorted(output, key=lambda row: row["id"])
    return {
        "event": {**event, "closure_hold": CLOSURE_HOLD},
        "jobs": ordered,
        "gaps": _gaps(ordered, calendar, event),
        "late": [{"id": row["id"], "line": row["line"], "minutes": row["late_minutes"],
                  "stage": row["stage"], "relocated": row["relocated"]}
                 for row in ordered if row["late_minutes"] > 0],
        "summary": _summary(ordered, event),
    }


def _seed(holds, job):
    holds["stage:" + job["stage"]].append(
        {"id": job["id"], "start": job["start"], "end": job["stage_end"]})
    holds["tech:" + job["tech"]].append(
        {"id": job["id"], "start": job["start"], "end": job["end"]})


def _gaps(rows, calendar, event):
    placed = [row for row in rows if row["status"] == "scheduled"]
    gaps = []
    for name in calendar["stages"]:
        windows = calendar["effective_stages"][name]
        busy = sorted((row["start"], row["stage_end"]) for row in placed if row["stage"] == name)
        for left, right in windows:
            cursor = left
            for start, end in busy:
                if end <= cursor:
                    continue
                if start >= right:
                    break
                if start > cursor:
                    gaps.append({"stage": name, "start": cursor, "end": min(start, right),
                                 "minutes": min(start, right) - cursor})
                cursor = max(cursor, end)
            if cursor < right:
                gaps.append({"stage": name, "start": cursor, "end": right, "minutes": right - cursor})
    for gap in gaps:
        gap["cause"] = (event["id"] if gap["stage"] == event["stage"]
                        and overlaps((gap["start"], gap["end"]), (event["start"], event["end"]))
                        else "排程空档")
    return gaps


def _summary(rows, event):
    def entry(status):
        return sum(row["entry_status"] == status for row in rows)
    return {
        "closure_id": event["id"],
        "stage": event["stage"],
        "window": [event["start"], event["end"]],
        "as_of": event["as_of"],
        "backup_stage": event["backup_stage"],
        "locked": entry("locked"),
        "active": entry("active"),
        "waiting": entry("waiting"),
        "relocated": sum(row["recovery_status"] == "relocated" for row in rows),
        "pending": sum(row["status"] != "scheduled" for row in rows),
        "late": sum(row["late_minutes"] > 0 for row in rows),
    }
