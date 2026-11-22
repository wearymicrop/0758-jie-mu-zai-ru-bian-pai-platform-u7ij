from app.config import RULE_VERSION
from app.manifest import canonical, sha


def recovery_manifest(source, event):
    base = {name: sha(canonical(source[name])) for name in ("orders", "calendar")}
    event_hash = sha(canonical(event))
    return {"rule_version": RULE_VERSION, "files": base, "closure_event": event_hash,
            "digest": sha(canonical([RULE_VERSION, base, event_hash]))}
