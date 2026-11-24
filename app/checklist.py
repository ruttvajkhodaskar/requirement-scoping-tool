from app.schemas import CATEGORIES, ScopingResult


def build_checklist(result: ScopingResult) -> str:
    """Make a simple markdown checklist for the estimating team."""
    lines = ["# Estimating Checklist", ""]
    for cat in CATEGORIES:
        items = [r.detail for r in result.requirements if r.category == cat]
        if items:
            lines.append(f"- [x] **{cat}**: " + " | ".join(items))
        else:
            lines.append(f"- [ ] **{cat}**: MISSING - ask the customer")
    others = [r.detail for r in result.requirements if r.category not in CATEGORIES]
    if others:
        lines.append("")
        lines.append("## Other notes")
        lines += [f"- {o}" for o in others]
    return "\n".join(lines)
