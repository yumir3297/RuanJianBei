import test from "node:test";
import assert from "node:assert/strict";

import { httpErrorMessage } from "../src/utils/httpErrorMessage.js";

test("prefers the actionable API stage message over the generic HTTP error", () => {
  const error = {
    message: "Request failed with status code 503",
    response: {
      data: {
        error: "knowledge_chunk_prepare_failed",
        message: "切块准备失败，请检查内容后重试。",
      },
    },
  };

  assert.equal(httpErrorMessage(error), "切块准备失败，请检查内容后重试。");
});

test("supports FastAPI detail errors and ordinary JavaScript errors", () => {
  assert.equal(httpErrorMessage({ response: { data: { detail: "index conflict" } } }), "index conflict");
  assert.equal(httpErrorMessage(new Error("network down")), "network down");
});
