/**
 * 应急/服务电话渲染与拨号逻辑。
 *
 * 安全规则：
 * - 只有 status === 'verified' 且 phoneUri 通过 tel: 白名单校验的条目才渲染“拨打”按钮；
 * - 未核验号码只展示文本与复制，并明确提示向现场工作人员求助；
 * - 从不声称“拨号成功/已接警”。
 */

export const CONTACTS_URL = "/offline/help/contacts.json";

const ENTRY_STATUS = new Set(["verified", "unverified", "expired"]);
const TEL_PATTERN = /^tel:\+?[0-9*#()-]{3,24}$/;

export function isDialable(entry) {
  return Boolean(
    entry &&
      entry.status === "verified" &&
      typeof entry.phoneUri === "string" &&
      TEL_PATTERN.test(entry.phoneUri),
  );
}

function normalizeEntry(raw, index) {
  if (!raw || typeof raw !== "object") return null;
  const phoneDisplay = typeof raw.phoneDisplay === "string" ? raw.phoneDisplay.trim().slice(0, 32) : "";
  if (!phoneDisplay) return null;
  const status = ENTRY_STATUS.has(raw.status) ? raw.status : "unverified";
  return {
    id: typeof raw.id === "string" && raw.id ? raw.id.slice(0, 48) : `entry-${index}`,
    group: raw.group === "emergency" ? "emergency" : "service",
    label: typeof raw.label === "string" ? raw.label.slice(0, 32) : "景区服务",
    phoneDisplay,
    phoneUri: typeof raw.phoneUri === "string" ? raw.phoneUri.trim() : "",
    verifiedAt: typeof raw.verifiedAt === "string" ? raw.verifiedAt : null,
    source: typeof raw.source === "string" ? raw.source : null,
    status,
  };
}

export function sanitizeContacts(raw) {
  const empty = {
    siteId: "",
    regionName: "",
    contactsVersion: "",
    verifiedAt: null,
    source: null,
    status: "unverified",
    entries: [],
  };
  if (!raw || typeof raw !== "object") return empty;
  const entries = Array.isArray(raw.entries)
    ? raw.entries.map(normalizeEntry).filter(Boolean)
    : [];
  return {
    siteId: typeof raw.siteId === "string" ? raw.siteId : "",
    regionName: typeof raw.regionName === "string" ? raw.regionName.slice(0, 48) : "",
    contactsVersion: typeof raw.contactsVersion === "string" ? raw.contactsVersion : "",
    verifiedAt: typeof raw.verifiedAt === "string" ? raw.verifiedAt : null,
    source: typeof raw.source === "string" ? raw.source : null,
    status: ENTRY_STATUS.has(raw.status) ? raw.status : "unverified",
    entries,
  };
}

export async function copyText(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // 回退到 execCommand 路径
  }
  try {
    const helper = document.createElement("textarea");
    helper.value = text;
    helper.setAttribute("readonly", "");
    helper.style.position = "fixed";
    helper.style.opacity = "0";
    document.body.appendChild(helper);
    helper.select();
    const copied = document.execCommand("copy");
    document.body.removeChild(helper);
    return copied;
  } catch {
    return false;
  }
}

function badge(text, tone) {
  const element = document.createElement("span");
  element.className = `contact-badge contact-badge--${tone}`;
  element.textContent = text;
  return element;
}

function createEntryCard(entry, notify) {
  const card = document.createElement("article");
  card.className = `contact-card contact-card--${entry.status}`;
  card.dataset.contactId = entry.id;

  const head = document.createElement("div");
  head.className = "contact-card-head";
  const name = document.createElement("strong");
  name.textContent = entry.label;
  head.appendChild(name);
  if (entry.status === "verified") head.appendChild(badge("已核验", "ok"));
  else if (entry.status === "expired") head.appendChild(badge("已失效", "danger"));
  else head.appendChild(badge("号码未核验", "warn"));
  card.appendChild(head);

  const number = document.createElement("p");
  number.className = "contact-number";
  number.textContent = entry.phoneDisplay;
  card.appendChild(number);

  const actions = document.createElement("div");
  actions.className = "contact-actions";

  if (isDialable(entry)) {
    const dial = document.createElement("a");
    dial.className = "contact-dial";
    dial.href = entry.phoneUri;
    dial.textContent = "拨打";
    dial.setAttribute("aria-label", `拨打${entry.label} ${entry.phoneDisplay}`);
    actions.appendChild(dial);
  }

  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "contact-copy";
  copy.textContent = "复制号码";
  copy.addEventListener("click", async () => {
    const ok = await copyText(entry.phoneDisplay);
    notify(ok ? "号码已复制" : "复制失败，请手动记录号码");
  });
  actions.appendChild(copy);
  card.appendChild(actions);

  if (entry.status !== "verified") {
    const note = document.createElement("p");
    note.className = "contact-note";
    note.textContent =
      entry.status === "expired"
        ? "该号码已过有效期，请勿依赖；请向附近工作人员求助。"
        : "该号码尚未完成官方核验，仅作参考；如无法联系，请向附近工作人员求助。";
    card.appendChild(note);
  }
  return card;
}

export function renderContacts(container, data, notify = () => {}) {
  container.replaceChildren();
  if (!data || !data.entries.length) {
    const empty = document.createElement("p");
    empty.className = "contact-empty";
    empty.textContent = "景区联系电话尚未配置，请向附近工作人员求助。";
    container.appendChild(empty);
    return;
  }

  if (data.status !== "verified") {
    const notice = document.createElement("p");
    notice.className = "contact-global-warning";
    notice.textContent = "以下号码来自景区后台配置，尚未完成官方核验，不作为官方救援电话使用。";
    container.appendChild(notice);
  }

  const groups = [
    { key: "emergency", title: "紧急求助" },
    { key: "service", title: "景区服务" },
  ];
  for (const group of groups) {
    const items = data.entries.filter((entry) => entry.group === group.key);
    if (!items.length) continue;
    const section = document.createElement("section");
    section.className = "contact-group";
    const heading = document.createElement("h3");
    heading.textContent = group.title;
    section.appendChild(heading);
    for (const entry of items) section.appendChild(createEntryCard(entry, notify));
    container.appendChild(section);
  }

  const footnote = document.createElement("p");
  footnote.className = "contact-footnote";
  footnote.textContent =
    "说明：网页只负责唤起系统拨号界面；是否接通取决于当前网络、SIM 卡与景区值班安排，页面不会确认“已接警”。";
  container.appendChild(footnote);
}
