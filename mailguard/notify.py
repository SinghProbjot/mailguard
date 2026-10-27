"""Windows notifications and the local log (JSONL)."""
from __future__ import annotations
import json
from datetime import datetime
from .paths import LOG, PROCESSED, FEEDBACK


def toast(title: str, msg: str):
    try:
        from winotify import Notification, audio
        n = Notification(app_id="MailGuard", title=title, msg=msg[:250], duration="long")
        n.set_audio(audio.Default, loop=False)
        n.show()
    except Exception as e:  # a notification must never block the analysis
        print(f"[notification failed: {e}]")


def log(record: dict):
    record["ts"] = datetime.now().isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def feedback(record: dict):
    record["ts"] = datetime.now().isoformat(timespec="seconds")
    with FEEDBACK.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_log(limit: int = 300) -> list[dict]:
    try:
        lines = LOG.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(l) for l in lines if l.strip()]
    except Exception:
        return []


def load_processed() -> set[str]:
    try:
        return set(json.loads(PROCESSED.read_text(encoding="utf-8")))
    except Exception:
        return set()


def save_processed(ids: set[str]):
    PROCESSED.write_text(json.dumps(sorted(ids)[-5000:]), encoding="utf-8")
