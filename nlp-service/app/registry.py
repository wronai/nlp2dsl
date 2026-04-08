"""
ACTIONS_REGISTRY — źródło prawdy.

Każda akcja definiuje:
  - required: pola wymagane do wygenerowania DSL
  - optional: pola opcjonalne z wartościami domyślnymi
  - aliases: słowa kluczowe (PL + EN) do dopasowania z NLP
  - description: opis dla GUI / API
  - param_aliases: mapowanie synonimów NLP → nazwy parametrów
"""

ACTIONS_REGISTRY: dict[str, dict] = {
    "send_invoice": {
        "description": "Generuje i wysyła fakturę",
        "required": ["amount", "to"],
        "optional": {"currency": "PLN"},
        "aliases": [
            "faktura", "fakturę", "invoice", "rachunek",
            "wyślij fakturę", "wystaw fakturę", "send invoice",
        ],
        "param_aliases": {
            "kwota": "amount",
            "suma": "amount",
            "cena": "amount",
            "waluta": "currency",
            "odbiorca": "to",
            "klient": "to",
            "do": "to",
            "adresat": "to",
        },
    },
    "send_email": {
        "description": "Wysyła e-mail",
        "required": ["to"],
        "optional": {"subject": "Automatyczna wiadomość", "body": ""},
        "aliases": [
            "email", "e-mail", "mail", "maila",
            "wyślij email", "wyślij maila", "send email",
            "wiadomość", "napisz",
        ],
        "param_aliases": {
            "temat": "subject",
            "treść": "body",
            "do": "to",
            "odbiorca": "to",
        },
    },
    "generate_report": {
        "description": "Generuje raport PDF/CSV",
        "required": ["report_type"],
        "optional": {"format": "pdf"},
        "aliases": [
            "raport", "report", "zestawienie", "sprawozdanie",
            "generuj raport", "zrób raport", "generate report",
        ],
        "param_aliases": {
            "typ": "report_type",
            "rodzaj": "report_type",
            "sprzedaż": "report_type=sales",
            "hr": "report_type=hr",
            "finanse": "report_type=finance",
            "format": "format",
            "pdf": "format=pdf",
            "csv": "format=csv",
        },
    },
    "crm_update": {
        "description": "Aktualizuje rekord w CRM",
        "required": ["entity"],
        "optional": {"data": {}},
        "aliases": [
            "crm", "aktualizuj crm", "update crm",
            "dodaj do crm", "wpis crm",
        ],
        "param_aliases": {
            "kontakt": "entity=contact",
            "klient": "entity=client",
            "lead": "entity=lead",
        },
    },
    "notify_slack": {
        "description": "Wysyła powiadomienie Slack",
        "required": ["channel"],
        "optional": {"message": "Automatyczne powiadomienie"},
        "aliases": [
            "slack", "powiadomienie", "powiadom", "notify",
            "wyślij na slack", "notify slack", "slack notification",
        ],
        "param_aliases": {
            "kanał": "channel",
            "wiadomość": "message",
        },
    },
    "notify_telegram": {
        "description": "Wysyła powiadomienie Telegram",
        "required": ["chat_id"],
        "optional": {"message": "Automatyczne powiadomienie"},
        "aliases": [
            "telegram", "telegramie", "powiadomienie telegram", "notify telegram",
            "wyślij na telegram", "telegram notification",
        ],
        "param_aliases": {
            "chat": "chat_id",
            "kanał": "chat_id",
            "wiadomość": "message",
            "message": "message",
        },
    },
    "notify_teams": {
        "description": "Wysyła powiadomienie Microsoft Teams",
        "required": ["channel"],
        "optional": {"message": "Automatyczne powiadomienie"},
        "aliases": [
            "teams", "microsoft teams", "powiadomienie teams", "notify teams",
            "wyślij na teams",
        ],
        "param_aliases": {
            "kanał": "channel",
            "wiadomość": "message",
            "message": "message",
        },
    },

    # ── Code Generation ────────────────────────────────────────

    "generate_code": {
        "description": "Generuje kod w wybranym języku programowania",
        "required": ["description"],
        "optional": {"language": "python", "context": None, "include_tests": False},
        "aliases": [
            "generuj kod", "napisz kod", "stwórz kod", "generate code",
            "write code", "create code", "kod", "program", "funkcja",
            "klasa", "skrypt", "aplikacja", "moduł", "implementuj",
            "napisz funkcję", "stwórz klasę", "zaimplementuj",
        ],
        "param_aliases": {
            "język": "language",
            "w języku": "language",
            "opis": "description",
            "zadanie": "description",
            "kontekst": "context",
            "testy": "include_tests",
            "python": "language=python",
            "javascript": "language=javascript",
            "java": "language=java",
            "c++": "language=cpp",
            "cpp": "language=cpp",
            "go": "language=go",
            "rust": "language=rust",
            "php": "language=php",
            "ruby": "language=ruby",
        },
    },

    # ── System / Settings ─────────────────────────────────────

    "system_settings_get": {
        "description": "Pokaż aktualne ustawienia systemu",
        "category": "system",
        "required": [],
        "optional": {"section": "all"},
        "aliases": [
            "pokaż ustawienia", "ustawienia", "settings", "konfiguracja",
            "pokaż konfigurację", "show settings", "show config",
            "jakie ustawienia", "jaki model", "jaki provider",
        ],
        "param_aliases": {
            "llm": "section=llm",
            "nlp": "section=nlp",
            "worker": "section=worker",
            "plik": "section=file_access",
        },
    },
    "system_settings_set": {
        "description": "Zmień ustawienie systemu",
        "category": "system",
        "required": ["setting_path", "setting_value"],
        "optional": {},
        "aliases": [
            "zmień ustawienie", "zmień model", "zmień provider",
            "zmień temperaturę", "change setting", "set model",
            "zmień tryb", "przełącz na", "użyj modelu",
            "ustaw model", "ustaw tryb", "ustaw temperaturę",
        ],
        "param_aliases": {
            "model": "setting_path=llm.model",
            "temperatura": "setting_path=llm.temperature",
            "provider": "setting_path=llm.provider",
            "tryb": "setting_path=nlp.default_mode",
            "timeout": "setting_path=worker.timeout_seconds",
        },
    },
    "system_settings_reset": {
        "description": "Resetuj ustawienia do domyślnych",
        "category": "system",
        "required": [],
        "optional": {"section": "all"},
        "aliases": [
            "resetuj ustawienia", "reset settings", "przywróć domyślne",
            "domyślne ustawienia", "reset config",
        ],
        "param_aliases": {},
    },

    # ── File Operations ───────────────────────────────────────

    "system_file_read": {
        "description": "Odczytaj plik z projektu",
        "category": "system",
        "required": ["file_path"],
        "optional": {"line_start": 0, "line_end": 0},
        "aliases": [
            "odczytaj plik", "otwórz plik", "read file",
            "pokaż kod", "wyświetl plik", "cat", "view file",
            "co jest w pliku", "pokaż zawartość pliku",
            "pokaż ten plik",
        ],
        "param_aliases": {},
    },
    "system_file_write": {
        "description": "Zapisz / edytuj plik w projekcie",
        "category": "system",
        "required": ["file_path", "content"],
        "optional": {"mode": "write"},
        "aliases": [
            "zapisz plik", "edytuj plik", "zmień plik", "write file",
            "nadpisz plik", "utwórz plik", "create file",
            "zmodyfikuj", "popraw plik",
        ],
        "param_aliases": {
            "dopisz": "mode=append",
            "nadpisz": "mode=write",
        },
    },
    "system_file_list": {
        "description": "Listuj pliki w katalogu projektu",
        "category": "system",
        "required": [],
        "optional": {"directory": ".", "pattern": "*"},
        "aliases": [
            "listuj pliki", "pokaż pliki", "list files", "ls",
            "jakie pliki", "struktura projektu", "tree",
            "pokaż katalog", "pokaż strukturę",
        ],
        "param_aliases": {},
    },

    # ── Registry Management ───────────────────────────────────

    "system_registry_list": {
        "description": "Pokaż zarejestrowane akcje i ich parametry",
        "category": "system",
        "required": [],
        "optional": {"category": "all"},
        "aliases": [
            "pokaż akcje", "lista akcji", "list actions", "jakie akcje",
            "co umiesz", "co potrafisz", "dostępne akcje", "help",
            "pomoc", "capabilities",
        ],
        "param_aliases": {
            "systemowe": "category=system",
            "biznesowe": "category=business",
        },
    },
    "system_registry_add": {
        "description": "Dodaj nową akcję do rejestru",
        "category": "system",
        "required": ["action_name", "action_description"],
        "optional": {"required_fields": [], "aliases": []},
        "aliases": [
            "dodaj akcję", "nowa akcja", "zarejestruj akcję",
            "add action", "register action", "create action",
        ],
        "param_aliases": {},
    },
    "system_registry_edit": {
        "description": "Edytuj istniejącą akcję w rejestrze",
        "category": "system",
        "required": ["action_name"],
        "optional": {"action_description": None, "required_fields": None, "aliases": None},
        "aliases": [
            "edytuj akcję", "zmień akcję", "edit action",
            "modyfikuj akcję", "update action",
        ],
        "param_aliases": {},
    },

    # ── System Status ─────────────────────────────────────────

    "system_status": {
        "description": "Pokaż status systemu (health, wersja, statystyki)",
        "category": "system",
        "required": [],
        "optional": {},
        "aliases": [
            "status", "status systemu", "system status", "health",
            "jak działa system", "diagnostyka", "info",
        ],
        "param_aliases": {},
    },
}


# ── Composite intents (multi-step) ───────────────────────────

COMPOSITE_INTENTS: dict[str, list[str]] = {
    "invoice_and_notify": ["send_invoice", "notify_slack"],
    "invoice_and_email": ["send_invoice", "send_email"],
    "report_and_email": ["generate_report", "send_email"],
    "report_and_notify": ["generate_report", "notify_slack"],
    "full_invoice_flow": ["send_invoice", "send_email", "notify_slack"],
    "full_report_flow": ["generate_report", "send_email", "notify_slack"],
}

# ── Action categories ─────────────────────────────────────────

SYSTEM_ACTIONS = {
    name for name, meta in ACTIONS_REGISTRY.items()
    if meta.get("category") == "system"
}

BUSINESS_ACTIONS = {
    name for name in ACTIONS_REGISTRY
    if name not in SYSTEM_ACTIONS
}


# ── Trigger aliases ───────────────────────────────────────────

TRIGGER_ALIASES: dict[str, str] = {
    "codziennie": "daily",
    "co dzień": "daily",
    "daily": "daily",
    "co tydzień": "weekly",
    "tygodniowo": "weekly",
    "weekly": "weekly",
    "co poniedziałek": "weekly",
    "co miesiąc": "monthly",
    "miesięcznie": "monthly",
    "monthly": "monthly",
    "ręcznie": "manual",
    "manual": "manual",
    "na żądanie": "manual",
    "jednorazowo": "once",
}


def get_action_by_alias(text: str) -> str | None:
    """Dopasuj tekst do akcji po aliasach."""
    text_lower = text.lower()
    best_match = None
    best_length = 0

    for action_name, meta in ACTIONS_REGISTRY.items():
        for alias in meta["aliases"]:
            if alias in text_lower and len(alias) > best_length:
                best_match = action_name
                best_length = len(alias)

    return best_match


def get_trigger(text: str) -> str:
    """Wykryj trigger z tekstu."""
    text_lower = text.lower()
    for alias, trigger in TRIGGER_ALIASES.items():
        if alias in text_lower:
            return trigger
    return "manual"


def get_required_fields(action: str) -> list[str]:
    """Zwróć wymagane pola dla akcji."""
    meta = ACTIONS_REGISTRY.get(action, {})
    return meta.get("required", [])


def get_defaults(action: str) -> dict:
    """Zwróć domyślne wartości opcjonalnych pól."""
    meta = ACTIONS_REGISTRY.get(action, {})
    return dict(meta.get("optional", {}))
