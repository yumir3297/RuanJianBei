export function proposalValidationMessage(status) {
  if (status === 'pass') return '已检查所填预算、必去和排除景点；步行、无障碍等条件需现场核实。';
  if (status === 'unverified') return '游览预算、停留或路段时长、景点约束或休息间隔可能尚未核实；步行、无障碍等条件需现场核实。';
  return '提案校验未通过或状态无法确认，请重新生成。';
}

export function proposalValidationAllowsConfirmation(status) {
  return status === 'pass' || status === 'unverified';
}
