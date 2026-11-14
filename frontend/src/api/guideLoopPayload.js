export function buildGuideLoopDraftPayload(form) {
  const { evidence_id, source_ref, knowledge_entry_id, knowledge_revision_id, ...draft } = form;
  return {
    ...draft,
    knowledge_entry_id: knowledge_entry_id || null,
    knowledge_revision_id: knowledge_revision_id || null,
    evidence: { evidence_id, source_ref },
  };
}
