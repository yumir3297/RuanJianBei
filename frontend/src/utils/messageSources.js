export function resolveEvidence(id, sources) {
  return (Array.isArray(sources) ? sources : []).find(source => source?.evidence_id === `证据${id}`) || null;
}
