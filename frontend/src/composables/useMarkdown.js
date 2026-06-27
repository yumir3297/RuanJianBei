import { marked } from "marked";
import DOMPurify from "dompurify";

let markdownEnabled = true;

function createEvidenceRenderer(sources) {
  const renderer = new marked.Renderer();

  renderer.paragraph = function paragraph(token) {
    const html = this.parser.parseInline(token.tokens);
    const processed = html.replace(
      /\[证据(\d+)\]/g,
      (_, id) => {
        const source = sources.find(s => s.evidence_id === `证据${id}`);
        const title = source?.title || "未知来源";
        const snippet = source?.snippet || "";
        return `<cite class="citation" data-evidence-id="${id}" title="${escapeAttr(title)}: ${escapeAttr(snippet)}">[${id}]</cite>`;
      }
    );
    return `<p>${processed}</p>\n`;
  };

  return renderer;
}

function escapeAttr(str) {
  return String(str).replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>");
}

export function renderMarkdown(text, sources = [], isStreaming = false) {
  if (!text) return "";

  // 流式期间显示纯文本
  if (isStreaming) {
    return escapeHtml(text);
  }

  if (!markdownEnabled) {
    return escapeHtml(text);
  }

  try {
    const renderer = createEvidenceRenderer(sources);
    const rawHtml = marked(text, { renderer, breaks: true });
    return DOMPurify.sanitize(rawHtml);
  } catch (err) {
    console.warn("Markdown render failed, fallback to plain text:", err);
    markdownEnabled = false;
    return escapeHtml(text);
  }
}
