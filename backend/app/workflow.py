"""
workflow.py — backward-compat shim.

Logika przeniesiona do:
  app/engine.py          — run_workflow() + _repo
  app/routers/workflow.py — /run, /history/*, /actions, /from-text
  app/routers/chat.py    — /chat/*
  app/routers/settings.py — /settings/*, /actions/schema/*
  app/routers/system.py  — /system/execute
"""

from .engine import NLP_SERVICE_URL, WORKER_URL, _repo, run_workflow  # noqa: F401
from .routers.workflow import router  # noqa: F401
