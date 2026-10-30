export function stableSnapshotStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableSnapshotStringify).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableSnapshotStringify(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function isProposalDraftStale(canonicalSnapshot, draftSnapshot) {
  return Boolean(canonicalSnapshot) && stableSnapshotStringify(draftSnapshot) !== canonicalSnapshot;
}
