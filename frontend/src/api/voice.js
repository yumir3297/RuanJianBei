import http from "./http";

export async function transcribeAudio(audioBlob) {
  const response = await http.post("/asr/transcribe", audioBlob, {
    headers: {
      "Content-Type": audioBlob.type || "audio/webm",
    },
    // Local SenseVoice can take longer on its first model load.
    timeout: 45000,
  });

  return response.data;
}

export function getTranscriptionErrorMessage(error) {
  const code = String(error?.code || "").toUpperCase();
  const message = String(error?.message || "").toLowerCase();
  if (code === "ECONNABORTED" || code === "ETIMEDOUT" || message.includes("timeout")) {
    return "语音识别等待超时，请稍后重试或改用文字输入。";
  }
  if (!error?.response) {
    return "无法连接语音识别服务，请确认前后端服务已启动。";
  }

  const status = error.response.status;
  const detail = error.response.data?.detail || error.response.data?.message;
  if (status === 413) return "录音文件过大，请缩短录音后重试。";
  if (status === 415) return "当前录音格式不受支持，请更换浏览器后重试。";
  if (status >= 500) return "语音识别服务暂时不可用，请稍后重试。";
  if (typeof detail === "string" && detail.trim()) return detail;
  return `语音识别请求失败（HTTP ${status}），请稍后重试。`;
}
