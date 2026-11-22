from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import web
from app.config import ROOT, RULE_VERSION, TITLE
from app.errors import DomainError, render_error
from app.preview import preview
from app.store import connection
from app.modules.orders.handler import router as orders_api
from app.modules.dependencies.handler import router as dependencies_api
from app.modules.calendars.handler import router as calendars_api
from app.modules.conflicts.handler import router as conflicts_api
from app.modules.schedule.handler import router as schedule_api
from app.modules.reconcile.handler import router as reconcile_api
from app.modules.dispatch.handler import router as dispatch_api

app = FastAPI(title=TITLE)
app.add_exception_handler(DomainError, render_error)
app.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")
for router in (orders_api, dependencies_api, calendars_api, conflicts_api, schedule_api, reconcile_api, dispatch_api, web.router):
    app.include_router(router)


@app.get("/api/health")
def health():
    with connection() as conn:
        conn.execute("SELECT 1").fetchone()
    return {"status": "ok", "rule_version": RULE_VERSION}


@app.get("/api/samples/{sample}")
def sample_result(sample: str):
    return preview(sample)
