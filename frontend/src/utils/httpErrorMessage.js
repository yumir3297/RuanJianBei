export function httpErrorMessage(error, fallback = "操作失败，请稍后重试。") {
  return error?.response?.data?.message
    || error?.response?.data?.detail
    || error?.message
    || fallback;
}
