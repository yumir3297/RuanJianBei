import http from "./http";

/**
 * 获取景点自动讲解文本与语音（后端复用数字人链路，密钥不出服务端）。
 * 首次生成需 LLM + TTS 串行，超时放宽到 30s。
 * @param {string} attraction 景点名称
 * @param {string} [ttsVoice] 可选音色
 * @returns {Promise<{attraction:string,text:string,base64_audio:string,duration_ms:number,provider:string,cached:boolean,available:boolean,reason:string}>}
 */
export async function fetchSpotNarration(attraction, ttsVoice) {
  const payload = { attraction };
  if (ttsVoice) payload.tts_voice = ttsVoice;
  const { data } = await http.post("/guide/narration", payload, { timeout: 30000 });
  return data;
}
