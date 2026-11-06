export function isItineraryEditIntent(value) {
  const hasPlan = /行程|路线|景点|停留点|停留时间|停留时长|游览顺序/.test(value);
  const hasEdit = /调整|修改|改一下|改成|改为|重新规划|重新安排|换成|替换|删除|移除|增加|添加|加入|移动|避开|少走/.test(value);
  return (hasPlan && hasEdit) || /(?:加|增加|添加|去掉|删除|换掉).{0,8}(?:景点|停留点)/.test(value);
}
