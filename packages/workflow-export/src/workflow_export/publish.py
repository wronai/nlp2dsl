"""Shared publish-layer export (markpact + pactown) for examples and artifacts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from dsl_contracts import action_catalog_payload, contract_from_registry_entry

from .markpact import MarkpactExportBundle, export_markpact_bundle
from .pactown import PactownExportBundle, export_pactown_bundle

DEFAULT_BACKEND_URL = "http://localhost:8010"

_FALLBACK_CONTRACTS = {
    "generate_report": contract_from_registry_entry(
        "generate_report",
        {
            "description": "Generuje raport",
            "required": ["report_type"],
            "optional": {"format": "pdf"},
        },
    ),
    "send_email": contract_from_registry_entry(
        "send_email",
        {
            "description": "Wysyła e-mail",
            "required": ["to", "subject", "body"],
            "quality_required": ["body"],
        },
    ),
    "send_invoice": contract_from_registry_entry(
        "send_invoice",
        {
            "description": "Wysyła fakturę",
            "required": ["amount", "to"],
            "optional": {"currency": "PLN"},
        },
    ),
    "notify_slack": contract_from_registry_entry(
        "notify_slack",
        {
            "description": "Powiadomienie Slack",
            "optional": {"channel": "#general", "message": ""},
            "quality_required": ["message"],
        },
    ),
}


@dataclass
class PublishExportBundle:
    markpact: MarkpactExportBundle
    pactown: PactownExportBundle


@dataclass
class PublishValidationResult:
    markpact: str
    pactown: str
    ok: bool
    skipped: bool

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "markpact": self.markpact,
            "pactown": self.pactown,
            "ok": self.ok,
            "skipped": self.skipped,
        }


def catalog_from_nlp_client(client: Any | None) -> dict[str, Any]:
    """Fetch /nlp/actions or return minimal fallback catalog."""
    if client is not None:
        try:
            resp = client._nlp_service("GET", "/nlp/actions")
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, dict) and payload:
                return payload
        except Exception:
            pass
    return action_catalog_payload(_FALLBACK_CONTRACTS)


def export_workflow_publish_layer(
    artifact_root: Path | str,
    dsl: Mapping[str, Any],
    catalog: Mapping[str, Any],
    *,
    source_query: str = "",
    title: str | None = None,
    backend_url: str | None = None,
) -> PublishExportBundle:
    """Write markpact + pactown trees under artifact_root/generated/."""
    root = Path(artifact_root)
    backend = backend_url or os.environ.get("NLP2DSL_BACKEND_URL", DEFAULT_BACKEND_URL)
    markpact = export_markpact_bundle(
        root / "generated" / "markpact",
        dsl,
        catalog,
        title=title,
        backend_url=backend,
        source_query=source_query,
    )
    pactown = export_pactown_bundle(
        root / "generated" / "pactown",
        markpact_readme=markpact.readme,
    )
    return PublishExportBundle(markpact=markpact, pactown=pactown)


def validate_publish_layer_result(
    bundle: PublishExportBundle,
    *,
    require_packages: bool = False,
) -> PublishValidationResult:
    """Validate exported markpact/pactown artifacts when packages are available."""
    report: dict[str, str] = {}
    markpact_ok = False
    pactown_ok = False

    try:
        from markpact.parser import parse_blocks

        n = len(parse_blocks(bundle.markpact.readme.read_text(encoding="utf-8")))
        report["markpact"] = f"{n} blocks OK"
        markpact_ok = n > 0
    except ImportError:
        report["markpact"] = "skipped (markpact not installed)"
    except Exception as exc:
        report["markpact"] = f"error: {exc}"

    try:
        from pactown.config import load_config

        cfg = load_config(bundle.pactown.ecosystem_yaml)
        report["pactown"] = f"{cfg.name}: {len(cfg.services)} services OK"
        pactown_ok = len(cfg.services) > 0
    except ImportError:
        report["pactown"] = "skipped (pactown not installed)"
    except Exception as exc:
        report["pactown"] = f"error: {exc}"

    skipped = report["markpact"].startswith("skipped") and report["pactown"].startswith("skipped")
    if require_packages and skipped:
        if report["markpact"].startswith("skipped"):
            report["markpact"] = "error: markpact required but not installed"
        if report["pactown"].startswith("skipped"):
            report["pactown"] = "error: pactown required but not installed"
        markpact_ok = False
        pactown_ok = False
        skipped = False

    ok = markpact_ok and pactown_ok and not any(msg.startswith("error:") for msg in report.values())
    return PublishValidationResult(
        markpact=report["markpact"],
        pactown=report["pactown"],
        ok=ok,
        skipped=skipped,
    )


def validate_publish_layer(bundle: PublishExportBundle) -> dict[str, str]:
    """Legacy dict report for examples."""
    result = validate_publish_layer_result(bundle)
    return {"markpact": result.markpact, "pactown": result.pactown}


def assert_publish_layer_valid(
    bundle: PublishExportBundle,
    *,
    require_packages: bool = True,
) -> PublishValidationResult:
    """Validate export bundle; raises ValueError when validation fails."""
    result = validate_publish_layer_result(bundle, require_packages=require_packages)
    if not result.ok and not (result.skipped and not require_packages):
        raise ValueError(f"Publish layer validation failed: {result.to_dict()}")
    return result


def print_publish_summary(bundle: PublishExportBundle, *, validation: Mapping[str, str] | None = None) -> None:
    print("✅ Export markpact + pactown:")
    print(f"   markpact README: {bundle.markpact.readme}")
    print(f"   pactown ecosystem: {bundle.pactown.ecosystem_yaml}")
    if validation:
        for key, msg in validation.items():
            icon = "🔍" if "OK" in msg else "💡" if "skipped" in msg else "⚠️"
            print(f"   {icon} {key}: {msg}")
