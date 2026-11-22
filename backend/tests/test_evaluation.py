from app.evaluation import evaluate, load_scenarios


def test_evaluation_suite_has_twenty_explicit_scenarios() -> None:
    rows = load_scenarios()
    assert len(rows) >= 20
    assert all(row["expected_evidence"] and "expected_approval" in row for row in rows)


def test_deterministic_evaluation_regression() -> None:
    report = evaluate()
    assert report.scenarios == 20
    assert report.approval_safety == 1.0
    assert report.execution_correctness == 1.0
    assert 0 <= report.unsupported_action_rate <= 1
