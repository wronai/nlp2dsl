"""
workflow.py — backward-compat shim.

Logika przeniesiona do:
  app/engine.py          — run_workflow() + _repo
  app/routers/workflow.py — /run, /history/*, /actions, /from-text
  app/routers/chat.py    — /chat/*
  app/routers/settings.py — /settings/*, /actions/schema/*
  app/routers/system.py  — /system/execute
"""

from app.engine import NLP_SERVICE_URL as _NLP_SERVICE_URL
from app.engine import WORKER_URL as _WORKER_URL
from app.engine import _repo as __repo
from app.engine import run_workflow as __run_workflow
from app.routers.workflow import router as __router

NLP_SERVICE_URL = _NLP_SERVICE_URL
WORKER_URL = _WORKER_URL
_repo = __repo
run_workflow = __run_workflow
router = __router
