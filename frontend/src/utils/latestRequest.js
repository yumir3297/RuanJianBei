// Keep one in-flight operation per consumer and ignore late outcomes after cancellation.
export function createLatestRequest() {
  let controller = null;
  let generation = 0;
  function cancel() {
    generation += 1;
    controller?.abort();
    controller = null;
  }
  function begin() {
    cancel();
    controller = new AbortController();
    const current = controller;
    const token = generation;
    return { signal: current.signal, isCurrent: () => generation === token && controller === current };
  }
  return { begin, cancel };
}
