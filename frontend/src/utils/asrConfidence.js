export function displayableASRConfidence(result) {
  const confidence = result?.confidence;
  return result?.confidence_source === 'provider' && Number.isFinite(confidence) && confidence >= 0 && confidence <= 1
    ? confidence : -1;
}
