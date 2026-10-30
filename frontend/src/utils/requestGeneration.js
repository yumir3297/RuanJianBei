export function createRequestGeneration() {
  let sequence = 0;
  let active = null;

  return {
    begin() {
      active?.controller.abort();
      const request = { id: ++sequence, controller: new AbortController() };
      active = request;
      return { id: request.id, signal: request.controller.signal };
    },
    isCurrent(request) {
      return Boolean(active && request?.id === active.id && !active.controller.signal.aborted);
    },
    finish(request) {
      if (!this.isCurrent(request)) return false;
      active = null;
      return true;
    },
    cancel() {
      if (!active) return false;
      active.controller.abort();
      active = null;
      return true;
    },
  };
}
