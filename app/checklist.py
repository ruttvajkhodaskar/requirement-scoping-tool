from app.schemas import CATEGORIES, ScopingResult


def build_checklist(result: ScopingResult) -> str:
    """Markdown checklist for the estimating team."""
    lines = ["# Estimating Checklist", ""]
    for cat in CATEGORIES:
        items = [r for r in result.requirements if r.category == cat]
        good = [r for r in items if not r.needs_review]
        if good:
            lines.append(f"- [x] **{cat}**: " + " | ".join(r.detail for r in good))
        elif items:
            lines.append(f"- [ ] **{cat}**: UNCLEAR, please confirm - " + " | ".join(r.detail for r in items))
        else:
            lines.append(f"- [ ] **{cat}**: MISSING - ask the customer")
    others = [r.detail for r in result.requirements if r.category not in CATEGORIES]
    if others:
        lines += ["", "## Other notes"] + [f"- {o}" for o in others]
    return "\n".join(lines)
