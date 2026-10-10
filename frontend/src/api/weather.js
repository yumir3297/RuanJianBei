import http from "./http";

/**
 * 实时天气 + 景区预警颜色 + 空气质量（后端代理和风天气，密钥不出服务端）。
 * @param {{ lat?: number, lon?: number }} [params] 不传则使用后端配置的景区默认坐标
 * @returns {Promise<object>} 归一化后的天气数据（available/weather/alert/air）
 */
export async function fetchCurrentWeather(params = {}) {
  const { data } = await http.get("/weather/current", {
    params,
    timeout: 12000,
  });
  return data;
}
