from app.services.qa.answer_styler import polish_answer


def resolve_final_answer(
    *,
    generated_answer: str,
    degraded: bool,
    faq_documents_present: bool,
    faq_answer: str,
    persona: str,
    faq_sources: list[dict],
) -> str:
    """Choose the canonical answer before it is spoken, cached, or persisted."""
    if degraded and faq_documents_present:
        return polish_answer(faq_answer, persona, faq_sources)
    return generated_answer
