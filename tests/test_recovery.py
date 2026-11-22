import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.config import db_path
from app.errors import DomainError
from app.sources import load_sample
from app.modules.recovery.archive import build_recovery, create_recovery, rerun_recovery
from app.modules.recovery.checklist import build_recovery_checklist
from app.modules.recovery.manifest import recovery_manifest
from app.modules.recovery.planner import plan_recovery

CLOSURE = {"id": "LOCK-720", "stage": "主舞台", "start": 720, "end": 840,
           "as_of": 720, "backup_stage": "侧舞台"}


def recovery_of(client_or_source, event=CLOSURE):
    source = client_or_source
    return build_recovery(source, event)[2]


def test_locked_work_is_kept_as_fact(dirty):
    recovery = plan_recovery(dirty, CLOSURE)
    locked = {job["id"]: job for job in recovery["jobs"] if job["entry_status"] == "locked"}
    assert set(locked) == {"A01", "A02", "C04"}
    assert (locked["A01"]["start"], locked["A01"]["end"]) == (605, 640)
    assert locked["C04"]["recovery_status"] == "locked"


def test_started_work_is_active_and_unstarted_is_waiting(dirty):
    recovery = plan_recovery(dirty, CLOSURE)
    status = {job["id"]: job for job in recovery["jobs"]}
    assert status["A03"]["entry_status"] == "active"
    assert {status[key]["entry_status"] for key in ("A04", "A05")} == {"waiting"}


def test_backup_stage_only_wins_on_strictly_earlier_slot(dirty):
    recovery = plan_recovery(dirty, CLOSURE)
    moved = {job["id"]: job for job in recovery["jobs"] if job["relocated"]}
    assert set(moved) == {"A03"}
    a03 = moved["A03"]
    assert (a03["stage"], a03["start"], a03["end"]) == ("侧舞台", 825, 865)
    assert a03["original_stage"] == "主舞台" and "H03" in a03["related"]
    # 备用舞台不更早时，等待工序留在原工位
    a04 = next(job for job in recovery["jobs"] if job["id"] == "A04")
    assert a04["relocated"] is False and a04["stage"] == "主舞台"
    assert (a04["start"], a04["end"]) == (865, 910)


def test_no_backup_keeps_everything_on_original_stage(dirty):
    event = {**CLOSURE, "backup_stage": None}
    recovery = plan_recovery(dirty, event)
    placed = [job for job in recovery["jobs"] if job["status"] == "scheduled"]
    main = [job for job in placed if job["original_stage"] == "主舞台"]
    assert all(job["stage"] == "主舞台" for job in main)
    assert all(job["relocated"] is False for job in main)
    a03 = next(job for job in recovery["jobs"] if job["id"] == "A03")
    assert a03["entry_status"] == "active" and a03["recovery_status"] == "active"
    assert (a03["start"], a03["end"]) == (855, 895)


def test_tie_break_prefers_original_stage(dirty):
    event = {"id": "TIE", "stage": "主舞台", "start": 720, "end": 840,
             "as_of": 690, "backup_stage": "侧舞台"}
    recovery = plan_recovery(dirty, event)
    a02 = next(job for job in recovery["jobs"] if job["id"] == "A02")
    # 两侧同为 825 可开工 -> 原工位优先；A02 被侧台既有工序推后才不改场
    assert a02["relocated"] is True and a02["start"] == 825
    same = plan_recovery(dirty, {**event, "backup_stage": None})
    a02_home = next(job for job in same["jobs"] if job["id"] == "A02")
    assert a02_home["stage"] == "主舞台" and a02_home["start"] >= a02["start"]


def test_deadlines_never_extend_and_late_is_reported(dirty):
    recovery = plan_recovery(dirty, CLOSURE)
    assert recovery["late"] == [{"id": "A03", "line": 3, "minutes": 145,
                                 "stage": "侧舞台", "relocated": True}]
    a03 = next(job for job in recovery["jobs"] if job["id"] == "A03")
    assert a03["late_minutes"] == 145


def test_gaps_include_closure_cause_and_idle_minutes(dirty):
    recovery = plan_recovery(dirty, CLOSURE)
    closure_gaps = [gap for gap in recovery["gaps"] if gap["cause"] == "LOCK-720"]
    assert [(gap["start"], gap["end"]) for gap in closure_gaps] == [
        (695, 750), (780, 840)]
    assert sum(gap["minutes"] for gap in closure_gaps) == 115
    assert all(gap["stage"] == "主舞台" for gap in closure_gaps)
    assert all(gap["minutes"] == gap["end"] - gap["start"] for gap in recovery["gaps"])


def test_replanned_jobs_never_collide(dirty):
    recovery = plan_recovery(dirty, CLOSURE)
    placed = [job for job in recovery["jobs"] if job["status"] == "scheduled"]
    for left in placed:
        for right in placed:
            if left["id"] >= right["id"]:
                continue
            if left["stage"] == right["stage"]:
                assert not (left["start"] < right["stage_end"] and right["start"] < left["stage_end"])
            if left["tech"] == right["tech"]:
                assert not (left["start"] < right["end"] and right["start"] < left["end"])
    for job in placed:
        if job["stage"] == "主舞台":
            assert not (job["start"] < 840 and 720 < job["end"])


def test_pending_and_isolated_evidence_is_preserved(dirty):
    recovery = plan_recovery(dirty, CLOSURE)
    pending = {job["id"]: job for job in recovery["jobs"] if job["status"] != "scheduled"}
    assert pending["X05"]["code"] == "NO_WINDOW"
    assert pending["X06"]["code"] == "DEPENDENCY_BLOCKED" and pending["X06"]["related"] == ["X05"]
    assert pending["X04"]["code"] == "UNKNOWN_STAGE"


def test_full_closure_turns_affected_jobs_pending_with_evidence(dirty):
    event = {"id": "FULL", "stage": "主舞台", "start": 720, "end": 1140}
    recovery = plan_recovery(dirty, event)
    by_id = {job["id"]: job for job in recovery["jobs"]}
    assert by_id["A03"]["status"] == "pending" and by_id["A03"]["code"] == "RESOURCE_FULL"
    assert "停场封场" in by_id["A03"]["related"]
    assert by_id["A04"]["code"] == "DEPENDENCY_BLOCKED"


def test_uncertain_resources_remain_excluded_during_recovery(dirty):
    # 脏日历含未知资源预约 H05，恢复重排不得把待核实资源纳入分配
    assert any(issue["id"] == "H05" for issue in dirty["conflicts"]["issues"])
    recovery = plan_recovery(dirty, CLOSURE)
    placed = [job for job in recovery["jobs"] if job["status"] == "scheduled"]
    assert all(job["stage"] != "不存在" for job in placed)


def test_recovery_covers_every_baseline_job_once(dirty):
    recovery = plan_recovery(dirty, CLOSURE)
    baseline_ids = {job["id"] for job in dirty["schedule"]["jobs"]}
    recovered_ids = [job["id"] for job in recovery["jobs"]]
    assert len(recovered_ids) == len(baseline_ids)
    assert set(recovered_ids) == baseline_ids
    checklist = build_recovery_checklist(recovery, dirty["calendars"])
    listed = {step["id"] for stage in checklist["stages"] for step in stage["steps"]}
    deferred = {item["id"] for item in checklist["deferred"]}
    assert listed | deferred == baseline_ids and listed.isdisjoint(deferred)


def test_deterministic_across_repeated_runs(dirty):
    first = plan_recovery(dirty, CLOSURE)
    second = plan_recovery(dirty, dict(CLOSURE))
    assert first == second


@pytest.mark.parametrize("event,code", [
    ({"id": "B1", "stage": "主舞台", "start": 840, "end": 720}, "BAD_CLOSURE"),
    ({"id": "B2", "stage": "不存在", "start": 720, "end": 840}, "BAD_CLOSURE"),
    ({"id": "B3", "stage": "主舞台", "start": 720, "end": 840, "backup_stage": "主舞台"}, "BAD_CLOSURE"),
    ({"id": "B4", "stage": "主舞台", "start": 720, "end": 840, "as_of": 800,
      "backup_stage": "侧舞台"}, "BAD_CLOSURE"),
    ({"id": "B5", "stage": "主舞台", "start": 1200, "end": 1260}, "BAD_CLOSURE"),
])
def test_invalid_closure_events(dirty, event, code):
    with pytest.raises(DomainError) as exc:
        plan_recovery(dirty, event)
    assert exc.value.code == code


def test_checklist_shares_the_same_result(dirty):
    recovery = plan_recovery(dirty, CLOSURE)
    checklist = build_recovery_checklist(recovery, dirty["calendars"])
    placed_ids = {job["id"] for stage in checklist["stages"] for job in stage["steps"]}
    assert placed_ids == {job["id"] for job in recovery["jobs"] if job["status"] == "scheduled"}
    moved = next(step for stage in checklist["stages"] for step in stage["steps"] if step["id"] == "A03")
    assert moved["relocated"] is True and moved["technician"] == "乔菲"
    assert checklist["gaps"] == recovery["gaps"] and checklist["late"] == recovery["late"]


def test_archive_idempotent_same_event_single_record(client):
    source = load_sample("dirty")
    first = create_recovery(source, CLOSURE)
    second = create_recovery(source, dict(CLOSURE))
    assert first["id"] == second["id"]
    assert first["reused"] is False and second["reused"] is True
    with sqlite3.connect(db_path()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM recoveries").fetchone()[0] == 1


def test_concurrent_recovery_requests_collapse_to_one(client):
    source = load_sample("dirty")
    with ThreadPoolExecutor(4) as pool:
        records = list(pool.map(lambda _: create_recovery(source, CLOSURE), range(4)))
    assert len({record["id"] for record in records}) == 1
    assert [record["reused"] for record in records].count(False) == 1
    with sqlite3.connect(db_path()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM recoveries").fetchone()[0] == 1


def test_invalid_event_writes_nothing(client):
    from app.store import connection
    source = load_sample("dirty")
    with connection():  # 先建立归档表，再验证失败路径不产生任何恢复单
        pass
    with pytest.raises(DomainError):
        create_recovery(source, {"id": "BAD", "stage": "主舞台", "start": 900, "end": 800,
                                 "as_of": 720})
    with sqlite3.connect(db_path()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM recoveries").fetchone()[0] == 0


def test_rerun_matches_archived_snapshot(client):
    source = load_sample("dirty")
    record = create_recovery(source, CLOSURE)
    verified = rerun_recovery(record["id"])
    assert verified == {**record, "reused": True}


def test_distinct_events_get_distinct_sheets(client):
    source = load_sample("dirty")
    first = create_recovery(source, CLOSURE)
    other = create_recovery(source, {**CLOSURE, "id": "LOCK-OTHER", "end": 900})
    assert first["id"] != other["id"]
    with sqlite3.connect(db_path()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM recoveries").fetchone()[0] == 2


def test_manifest_changes_with_event_or_source(client):
    source = load_sample("dirty")
    base = recovery_manifest(source, CLOSURE)
    assert recovery_manifest(source, {**CLOSURE, "end": 900})["digest"] != base["digest"]
    clean = load_sample("clean")
    assert recovery_manifest(clean, CLOSURE)["digest"] != base["digest"]


def test_recovery_api_preview_and_archive_flow(client):
    payload = {"sample": "dirty", "closure": CLOSURE}
    preview = client.post("/api/recoveries/preview", json=payload).json()
    assert preview["result"]["summary"]["relocated"] == 1
    saved = client.post("/api/recoveries", json=payload).json()
    assert saved["result"] == preview["result"]
    again = client.post("/api/recoveries", json=payload).json()
    assert again["id"] == saved["id"] and again["reused"] is True
    fetched = client.get(f"/api/recoveries/{saved['id']}").json()
    assert fetched["id"] == saved["id"]
    rerun = client.post(f"/api/recoveries/{saved['id']}/rerun").json()
    assert rerun["reused"] is True
    export = client.get(f"/api/recoveries/{saved['id']}/export")
    assert export.headers["content-disposition"].startswith("attachment;")
    assert export.json()["result"]["summary"] == saved["result"]["summary"]


def test_recovery_api_preview_does_not_persist(client):
    from app.store import connection
    payload = {"sample": "dirty", "closure": CLOSURE}
    response = client.post("/api/recoveries/preview", json=payload)
    assert response.status_code == 200
    with connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM recoveries").fetchone()[0] == 0


def test_recovery_api_validation_and_missing(client):
    response = client.post("/api/recoveries", json={"sample": "dirty",
                                                    "closure": {"id": "X", "stage": "主舞台",
                                                                "start": 900, "end": 800}})
    assert response.status_code == 422 and response.json()["code"] == "BAD_CLOSURE"
    assert client.get("/api/recoveries/missing").status_code == 404
    response = client.post("/api/recoveries/preview", json={"sample": "dirty"})
    assert response.status_code == 422 and response.json()["code"] == "CHOOSE_SOURCE"


def test_recovery_with_custom_order_source(client):
    source = load_sample("clean")
    response = client.post("/api/recoveries/preview",
                           json={"orders": source["orders"], "calendar": source["calendar"],
                                 "closure": {**CLOSURE, "backup_stage": None}})
    assert response.status_code == 200
    summary = response.json()["result"]["summary"]
    assert summary["stage"] == "主舞台" and summary["relocated"] == 0
