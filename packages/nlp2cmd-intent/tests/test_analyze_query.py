"""analyze_query must work with lightweight QueryNormalizer (returns str)."""

from nlp2cmd_intent.input import analyze_query


def test_analyze_query_find_files():
    data = analyze_query("znajdz pliki *.py", include_plan=True)
    assert data["query"] == "znajdz pliki *.py"
    intent = data["intent_ir"]
    assert intent["intent"] == "find"
    plan = data.get("execution_plan_ir")
    assert plan is not None
    assert plan["steps"][0]["action"] == "shell_find"
