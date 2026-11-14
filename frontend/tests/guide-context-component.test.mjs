import test from "node:test";
import assert from "node:assert/strict";
import { readFile, writeFile, unlink } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { compileScript, parse } from "@vue/compiler-sfc";
import { createRenderer, defineComponent, h, nextTick, reactive, ref } from "vue";
import { wgs84ToGcj02 } from "../src/constants/narration.js";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sourcePath = resolve(frontendRoot, "src/components/guide/GuideContextStatus.vue");

function createHostRenderer() {
  const createNode = (type, text = "") => ({
    type, text, props: {}, children: [], parent: null, value: "", multiple: false,
    selected: false, selectedIndex: -1,
    addEventListener() {}, removeEventListener() {},
    get options() { return this.children.filter(child => child.type === "option"); },
  });
  function insert(node, parent, anchor = null) {
    if (node.parent) {
      const oldIndex = node.parent.children.indexOf(node);
      if (oldIndex >= 0) node.parent.children.splice(oldIndex, 1);
    }
    node.parent = parent;
    const index = anchor ? parent.children.indexOf(anchor) : -1;
    if (index < 0) parent.children.push(node); else parent.children.splice(index, 0, node);
  }
  return createRenderer({
    createElement: type => createNode(type),
    createText: text => createNode("#text", text),
    createComment: text => createNode("#comment", text),
    setText: (node, text) => { node.text = text; },
    setElementText: (node, text) => { node.text = text; node.children = []; },
    patchProp: (node, key, _previous, value) => { node.props[key] = value; node[key] = value; },
    insert,
    insertStaticContent(content, parent, anchor) {
      const node = createNode("#static", content);
      insert(node, parent, anchor);
      return [node, node];
    },
    remove(node) {
      if (!node.parent) return;
      const index = node.parent.children.indexOf(node);
      if (index >= 0) node.parent.children.splice(index, 1);
      node.parent = null;
    },
    parentNode: node => node.parent,
    nextSibling(node) {
      if (!node.parent) return null;
      return node.parent.children[node.parent.children.indexOf(node) + 1] || null;
    },
  });
}

function textContent(node) {
  return `${node.text || ""}${node.children.map(textContent).join("")}`;
}

function findButton(root, label) {
  const stack = [...root.children];
  while (stack.length) {
    const node = stack.shift();
    if (node.type === "button" && textContent(node).includes(label)) return node;
    stack.push(...node.children);
  }
  return null;
}

test("CASS panel displays weather adaptation and sends review through its proposal event", async () => {
  const source = await readFile(sourcePath, "utf8");
  const { descriptor, errors } = parse(source, { filename: sourcePath });
  assert.deepEqual(errors, []);
  const compiled = compileScript(descriptor, { id: "cass-context-component-test", inlineTemplate: true });
  const temporaryModule = resolve(dirname(sourcePath), `GuideContextStatus.test-${process.pid}.mjs`);
  const executable = compiled.content
    .replace('import { useGuideContext } from "../../composables/useGuideContext";', 'const useGuideContext = () => globalThis.__cassContextMock();')
    .replace('import GuideSafetyNotice from "./GuideSafetyNotice.vue";', 'import { h as __h } from "vue"; const GuideSafetyNotice = { props: ["event"], setup(props, { emit }) { return () => __h("div", [__h("strong", props.event?.simulated ? "安全提醒（演示数据）" : "安全提醒"), __h("button", { onClick: () => emit("clear") }, "我已了解")]); } };')
    .replace('from "../../guide/context"', 'from "../../guide/context.js"')
    .replace('from "../../guide/scenario"', 'from "../../guide/scenario.js"');
  await writeFile(temporaryModule, executable);

  const near = wgs84ToGcj02(31.4328, 120.0996);
  const far = wgs84ToGcj02(31.436, 120.0996);
  const coordinateEntry = (spot_code, title, point) => ({ spot_code, published_revision_id: "rev-1", title, latitude: point.lat, longitude: point.lng, coordinate_system: "GCJ-02", coordinate_evidence_id: `survey-${spot_code}` });
  const bootstrap = ref({ enabled: true, demo_enabled: true, site_id: "site-1", catalog: [coordinateEntry("far", "远处景点", far), coordinateEntry("tower", "古塔", near)], catalog_digest: "catalog-v1" });
  const state = ref({ status: "off", activeSafetyEvent: null });
  const result = ref(null);
  const tour = ref({ id: "tour-1", version: 2, snapshot: { schema_version: 2 }, progress: { progress_version: 1 } });
  const weatherDecision = {
    decision: { action: "full_narration", reason_codes: ["standard_context"] },
    reasons: ["演示天气适配"], rule_ids: ["DEMO_WEATHER_PRECIPITATION_ADAPTATION"],
    weather_adaptation: { kind: "precipitation", condition: "小雨", source: "内置演示场景", simulated: true },
    evidence_refs: [{ type: "simulated_weather", source: "内置演示场景" }],
    data_mode: "demo", simulated: true, expires_at: new Date(Date.now() + 60_000).toISOString(),
    evidence_status: { weather: "simulated", alerts: "none_verified", location: "demo_only" }, safety_events: [],
  };
  let currentBootstrap = () => Promise.resolve(bootstrap.value);
  const safety = reactive({ hold: false, resumeDemo() { this.hold = false; } });
  globalThis.__cassContextMock = () => ({
    bootstrap, state, result, busy: ref(false), error: ref(""), safety,
    fetchCurrentBootstrap: () => currentBootstrap(),
    enable: async () => { state.value = { status: "idle", activeSafetyEvent: null }; return true; },
    assess: async payload => {
      assessmentPayload = payload;
      if (assessmentDeferred) {
        return new Promise(resolve => {
          finishAssessment = () => {
            if (!contextInvalidated) result.value = { ...weatherDecision, reasons: ["旧情境评估"] };
            resolve(result.value);
          };
        });
      }
      result.value = weatherDecision;
      return weatherDecision;
    },
    stop: () => {}, dispatch: event => {
      if (["enable", "safety_cleared"].includes(event.type)) state.value = { status: "idle", activeSafetyEvent: null };
      if (event.type === "safety_raised") state.value = { status: "interrupted", activeSafetyEvent: event.safetyEvent };
      if (event.type === "context_changed") contextInvalidated = true;
    },
  });

  let proposalText = "";
  let narrationText = "";
  let assessmentPayload;
  let assessmentDeferred = false;
  let contextInvalidated = false;
  let finishAssessment;
  let app;
  try {
    const component = await import(`${pathToFileURL(temporaryModule).href}?v=${Date.now()}`);
    const Host = defineComponent({
      setup() {
        return () => h(component.default, {
          position: { lat: 31.429, lng: 120.1, wgs84: { lat: 31.4328, lng: 120.0996 }, accuracy: 12, observedAt: Date.now() }, locationMode: "real", mapActive: true,
          tour: tour.value,
          onProposal: value => { proposalText = value; },
          onAsk: value => { narrationText = value.query; },
        });
      },
    });
    const renderer = createHostRenderer();
    const root = { type: "root", props: {}, children: [], parent: null };
    app = renderer.createApp(Host);
    app.mount(root);

    const enable = findButton(root, "开启情境导览");
    assert.ok(enable);
    await enable.props.onClick();
    await nextTick();
    assert.equal(assessmentPayload.spot_code, "far");
    assert.equal("location_hint" in assessmentPayload, false);
    const nearbySuggestion = findButton(root, "按位置选择附近景点：古塔");
    assert.ok(nearbySuggestion, textContent(root));
    nearbySuggestion.props.onClick();
    await nextTick();
    const weatherDemo = findButton(root, "演示雨天讲解适配");
    assert.ok(weatherDemo);
    weatherDemo.props.onClick();
    await nextTick();
    assert.match(textContent(root), /模拟天气适配：小雨/);
    assert.match(textContent(root), /模拟，不作为安全证据/);
    await findButton(root, "按演示情境生成讲解").props.onClick();
    assert.match(narrationText, /介绍古塔/);
    narrationText = "";
    currentBootstrap = async () => ({ ...bootstrap.value, catalog_digest: 'new-version' });
    await findButton(root, "按演示情境生成讲解").props.onClick();
    await nextTick();
    assert.equal(narrationText, "");
    assert.match(textContent(root), /景点资料已更新/);
    currentBootstrap = () => Promise.resolve(bootstrap.value);
    findButton(root, "演示雨天讲解适配").props.onClick();
    await nextTick();
    let resolveBootstrap;
    currentBootstrap = () => new Promise(resolve => { resolveBootstrap = resolve; });
    const pendingNarration = findButton(root, "按演示情境生成讲解").props.onClick();
    tour.value = { ...tour.value, version: 3 };
    await nextTick();
    resolveBootstrap(bootstrap.value);
    await pendingNarration;
    assert.equal(narrationText, "");
    findButton(root, "演示雨天讲解适配").props.onClick();
    await nextTick();
    currentBootstrap = () => Promise.reject(new Error('offline'));
    await findButton(root, "按演示情境生成讲解").props.onClick();
    await nextTick();
    assert.equal(narrationText, "");
    assert.match(textContent(root), /无法核对景点资料/);
    currentBootstrap = () => Promise.resolve(bootstrap.value);
    findButton(root, "演示客流变化").props.onClick();
    await nextTick();
    const proposal = findButton(root, "生成路线调整提案");
    assert.ok(proposal, textContent(root));
    proposal.props.onClick();
    assert.match(proposalText, /剩余时间预算/);
    proposalText = "";
    safety.hold = true;
    await nextTick();
    assert.equal(proposal.props.disabled, true);
    proposal.props.onClick();
    assert.equal(proposalText, "");
    safety.hold = false;
    await nextTick();

    assessmentDeferred = true;
    findButton(root, "评估当前情境").props.onClick();
    await nextTick();
    tour.value = { ...tour.value, version: 4 };
    await nextTick();
    finishAssessment();
    await nextTick();
    assert.equal(result.value, null);
    assessmentDeferred = false;

    findButton(root, "演示预警抢占").props.onClick();
    await nextTick();
    findButton(root, "继续演示：模拟预警变化").props.onClick();
    await nextTick();
    assert.match(textContent(root), /安全提醒（演示数据）/);
    findButton(root, "我已了解").props.onClick();
    await nextTick();
    findButton(root, "继续演示（需再次确认）").props.onClick();
    await nextTick();
    assert.match(textContent(root), /演示流程人工恢复/);
  } finally {
    app?.unmount();
    delete globalThis.__cassContextMock;
    await unlink(temporaryModule).catch(() => {});
  }
});
