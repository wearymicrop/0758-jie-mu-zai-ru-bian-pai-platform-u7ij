import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE = "节目载入编排台"
RULE_VERSION = "tandem-stage-1.0"
SOURCES = ('orders', 'calendar')


def db_path():
    return Path(os.environ.get("DB_PATH", ROOT / "instance/ledger.sqlite3"))
