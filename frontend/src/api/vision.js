import http from "./http";

export async function analyzeImage(file, question = "这张图片可能对应景区哪个位置？", options = {}) {
  const response = await http.post("/vision/analyze", file, {
    params: {
      question,
      filename: file.name,
    },
    headers: {
      "Content-Type": file.type || "application/octet-stream",
      ...(options.idempotencyKey ? { "Idempotency-Key": options.idempotencyKey } : {}),
    },
    timeout: 120000,
    signal: options.signal,
  });
  return response.data;
}

export function getVisionErrorMessage(error) {
  const status = error?.response?.status;
  const detail = error?.response?.data?.detail;
  if (status === 429) return "图片识别服务繁忙，请稍后重试。";
  if (status === 413) return "图片过大，请压缩后重新选择。";
  if (status === 415 && typeof detail === "string" && detail.includes("动态")) return "暂不支持动态 WebP，请选择静态图片。";
  if (status === 415) return "图片格式不受支持，请选择 JPEG、PNG 或 WebP。";
  if (status === 400) return "图片文件损坏或不完整，请重新选择。";
  if (["ECONNABORTED", "ETIMEDOUT"].includes(error?.code)) return "识别等待超时，请重试。";
  return "图片识别暂时不可用，请检查网络后重试。";
}
