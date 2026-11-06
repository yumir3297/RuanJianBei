export function buildTourBudgetParams(currentStopRemainingMinutes) {
  return currentStopRemainingMinutes == null ? undefined : {
    current_stop_remaining_minutes: currentStopRemainingMinutes,
  };
}
