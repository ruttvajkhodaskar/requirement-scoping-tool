from eval.run_eval import load_cases, prf, run, score


def test_dataset_is_valid():
    cases = load_cases()
    assert len(cases) >= 20
    for c in cases:
        for value in c["expected"].values():
            assert value in c["text"].lower(), f"{c['id']}: '{value}' not in text"


def test_rule_mode_quality_gate():
    cases = load_cases()
    stats = score(cases, run(cases, "rules"), confident_only=True)
    tp = sum(s["tp"] for s in stats.values())
    fp = sum(s["fp"] for s in stats.values())
    fn = sum(s["fn"] for s in stats.values())
    assert prf(tp, fp, fn)[2] >= 0.85  # protects against accidental regressions
