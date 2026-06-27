import http from "./http";

export async function analyzeImage(file, question = "这张图片可能对应景区哪个位置？") {
  const response = await http.post("/vision/analyze", file, {
    params: {
      question,
      filename: file.name,
    },
    headers: {
      "Content-Type": file.type || "application/octet-stream",
    },
    timeout: 120000,
  });
  return response.data;
}
