from pathlib import Path

from app import extractor
from app.extractor import extract, extract_with_rules, finalize
from app.schemas import Requirement, ScopingResult

SAMPLES = Path(__file__).parent.parent / "samples"


def cats(result, only_good=True):
    return {r.category for r in result.requirements if not (only_good and r.needs_review)}


def test_transcript_categories():
    result = extract_with_rules((SAMPLES / "sample_transcript.txt").read_text())
    assert {"Quantity", "Material", "Dimensions", "Timeline", "Standards"} <= cats(result)
    assert any("budget" in q.lower() for q in result.open_questions)


def test_rfp_budget_found():
    assert "Budget" in cats(extract_with_rules((SAMPLES / "sample_rfp.txt").read_text()))


def test_is_word_is_not_a_standard():
    # "is 120" must not be read as the Indian standard "IS 120"
    result = extract_with_rules("The outer diameter is 120 mm.")
    assert "Standards" not in cats(result, only_good=False)


def test_keyword_only_is_flagged_not_trusted():
    result = extract_with_rules("Is there a budget for this?")
    budget = [r for r in result.requirements if r.category == "Budget"]
    assert budget and budget[0].needs_review
    assert any("budget" in q.lower() for q in result.open_questions)


def test_every_rule_item_has_source_in_text():
    text = (SAMPLES / "sample_transcript.txt").read_text()
    for r in extract_with_rules(text).requirements:
        assert r.source_sentence in text


def test_ungrounded_llm_item_is_flagged():
    text = "We need 500 pieces in steel."
    fake = ScopingResult(
        summary="x",
        requirements=[Requirement(category="Budget", detail="Budget 5 lakh", source_sentence="Budget is 5 lakh.", confidence=0.95)],
        open_questions=[],
    )
    out = finalize(fake, text, keep_summary=True)
    assert out.requirements[0].needs_review
    assert out.requirements[0].confidence <= 0.4


def test_unknown_category_becomes_other():
    text = "Packing in wooden crates please."
    fake = ScopingResult(
        summary="x",
        requirements=[Requirement(category="Packaging", detail="Wooden crates", source_sentence=text, confidence=0.9)],
        open_questions=[],
    )
    assert finalize(fake, text).requirements[0].category == "Other"


def test_llm_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("LLM_RETRY_DELAY", "0")
    calls = {"n": 0}

    def flaky(text):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("slow")
        return extractor._LLMResult(
            summary="Wants 10 nos.",
            requirements=[extractor._LLMRequirement(category="Quantity", detail="10 nos", source_sentence="Need 10 nos.", confidence=0.9)],
            open_questions=[],
        )

    monkeypatch.setattr(extractor, "_call_llm", flaky)
    result, mode = extract("Need 10 nos.")
    assert mode == "llm" and calls["n"] == 3
    assert result.summary == "Wants 10 nos."


def test_llm_failure_falls_back_to_rules(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("LLM_RETRY_DELAY", "0")
    monkeypatch.setattr(extractor, "_call_llm", lambda t: (_ for _ in ()).throw(RuntimeError("down")))
    result, mode = extract("We need 100 pieces in 4 weeks.")
    assert mode == "rules-fallback"
    assert "Quantity" in cats(result)
