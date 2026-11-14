export function withAttractionCode(raw, code) {
  const metadata = raw ? JSON.parse(raw) : {};
  if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
    throw new Error("现有元数据格式无效，无法修改景点编号");
  }
  const value = code.trim();
  if (value && !/^[A-Za-z0-9_-]{1,100}$/.test(value)) {
    throw new Error("景点编号仅支持字母、数字、下划线和短横线，最多 100 位");
  }
  if (value) metadata.attraction_id = value;
  else delete metadata.attraction_id;
  return Object.keys(metadata).length ? JSON.stringify(metadata) : null;
}

export function changedAttractionMetadata(raw, originalCode, code) {
  if (code === originalCode) return undefined;
  return withAttractionCode(raw, code);
}
