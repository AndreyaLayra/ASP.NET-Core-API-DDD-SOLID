def rule_based_review(diff: str) -> str:
    feedback = []

    # Controller assumindo regras de negócio
    if "Controller" in diff and "if (" in diff:
        feedback.append(
            "⚠️ **Controller Responsibility Alert**\n"
            "Business validations appear to be implemented inside a Controller. "
            "Consider moving these rules to the Application or Domain layer to "
            "improve separation of concerns and testability."
        )

    # Regra hardcoded suspeita
    if "@test.com" in diff:
        feedback.append(
            "⚠️ **Hardcoded Business Rule Detected**\n"
            "Hardcoded email-based rules reduce flexibility and may complicate future changes. "
            "Consider making this rule configurable or moving it to a dedicated policy."
        )

    # Métodos potencialmente grandes
    if diff.count("\n") > 200:
        feedback.append(
            "⚠️ **Large Change Set Detected**\n"
            "This pull request introduces a large diff. Consider splitting it into smaller, "
            "more focused changes to improve reviewability."
        )

    # Caso nada relevante seja encontrado
    if not feedback:
        feedback.append(
            "✅ **No Critical Architectural Issues Detected**\n"
            "The changes follow expected architectural boundaries and coding practices."
        )

    return "\n\n".join(feedback)