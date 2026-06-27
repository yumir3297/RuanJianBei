import http from "./http";

export async function transcribeAudio(audioBlob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");

  const response = await http.post("/asr/transcribe", audioBlob, {
    headers: {
      "Content-Type": audioBlob.type || "audio/webm",
    },
    timeout: 15000,
  });

  return response.data;
}
