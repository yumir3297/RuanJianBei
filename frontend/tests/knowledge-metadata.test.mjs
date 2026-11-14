import test from "node:test";
import assert from "node:assert/strict";
import { changedAttractionMetadata, withAttractionCode } from "../src/utils/knowledgeMetadata.js";

test("attraction code preserves unrelated metadata and validates input", () => {
  assert.deepEqual(JSON.parse(withAttractionCode('{"extraction_method":"ocr_mixed"}', ' A-1 ')),
    { extraction_method: "ocr_mixed", attraction_id: "A-1" });
  assert.deepEqual(JSON.parse(withAttractionCode('{"attraction_id":"old","other":1}', '')), { other: 1 });
  assert.throws(() => withAttractionCode('{invalid', 'A'));
  assert.throws(() => withAttractionCode('[]', 'A'));
  assert.throws(() => withAttractionCode(null, 'invalid code'));
});

test("unchanged legacy or opaque metadata is omitted from an edit", () => {
  assert.equal(changedAttractionMetadata('{"attraction_id":"历史 编号"}', '历史 编号', '历史 编号'), undefined);
  assert.equal(changedAttractionMetadata('{invalid', '', ''), undefined);
  assert.throws(() => changedAttractionMetadata('{invalid', '', 'new-code'));
});
