(() => {
if (window.__YT_KEY_IDEAS_READY__) return;
window.__YT_KEY_IDEAS_READY__ = true;

const API_URL = "http://127.0.0.1:5012/key-ideas";
const PANEL_ID = "yt-key-ideas-panel";
const STYLE_ID = "yt-key-ideas-style";

function getVideoUrl() {
  return location.href;
}

function sanitizeMarkdownHtml(html) {
  const allowedTags = new Set([
    "A", "BLOCKQUOTE", "BR", "CODE", "EM", "H1", "H2", "H3", "H4",
    "H5", "H6", "HR", "LI", "OL", "P", "PRE", "STRONG", "UL",
  ]);
  const template = document.createElement("template");
  template.innerHTML = html;

  for (const element of [...template.content.querySelectorAll("*")]) {
    if (!allowedTags.has(element.tagName)) {
      element.replaceWith(...element.childNodes);
      continue;
    }

    for (const attr of [...element.attributes]) {
      if (element.tagName !== "A" || attr.name !== "href") {
        element.removeAttribute(attr.name);
      }
    }

    if (element.tagName === "A") {
      const href = element.getAttribute("href") || "";
      if (!/^https?:\/\//i.test(href)) {
        element.removeAttribute("href");
      } else {
        element.setAttribute("target", "_blank");
        element.setAttribute("rel", "noreferrer");
      }
    }
  }

  return template.innerHTML;
}

function renderMarkdown(text) {
  const library = globalThis.marked;
  const parse =
    typeof library?.parse === "function"
      ? library.parse.bind(library)
      : typeof library?.marked === "function"
        ? library.marked.bind(library)
        : null;

  if (!parse) {
    return '<p>Markdown parser failed to load.</p>';
  }

  return sanitizeMarkdownHtml(parse(text || "", { gfm: true, breaks: true }));
}

function createPanel() {
  const panel = document.createElement("aside");
  panel.id = PANEL_ID;
  panel.innerHTML = `
    <div class="ytki-header">
      <div>
        <div class="ytki-title">Key Ideas</div>
        <div class="ytki-subtitle">Current YouTube video</div>
      </div>
      <button class="ytki-close" type="button" aria-label="Close">x</button>
    </div>
    <div class="ytki-status">Ready</div>
    <div class="ytki-output"></div>
  `;

  if (!document.getElementById(STYLE_ID)) {
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
    #${PANEL_ID} {
      position: fixed;
      top: 0;
      right: 0;
      bottom: 0;
      z-index: 2147483647;
      width: min(420px, calc(100vw - 32px));
      height: 100vh;
      max-height: 100vh;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-sizing: border-box;
      padding: 16px;
      border: 1px solid oklch(82% 0 0);
      border-right: 0;
      border-radius: 0;
      background: oklch(98% 0 0);
      color: oklch(18% 0 0);
      box-shadow: none;
      font: 13px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    }

    #${PANEL_ID} .ytki-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }

    #${PANEL_ID} .ytki-title {
      font-size: 15px;
      font-weight: 650;
      letter-spacing: 0;
    }

    #${PANEL_ID} .ytki-subtitle {
      margin-top: 2px;
      color: oklch(42% 0 0);
      font-size: 12px;
    }

    #${PANEL_ID} .ytki-close {
      border: 1px solid oklch(70% 0 0);
      border-radius: 0;
      background: oklch(96% 0 0);
      color: oklch(18% 0 0);
      font: inherit;
      cursor: pointer;
    }

    #${PANEL_ID} .ytki-close:hover {
      background: oklch(90% 0 0);
    }

    #${PANEL_ID} .ytki-close {
      width: 28px;
      height: 28px;
      line-height: 1;
    }

    #${PANEL_ID} .ytki-status {
      min-height: 18px;
      color: oklch(42% 0 0);
      font-size: 12px;
    }

    #${PANEL_ID} .ytki-output {
      flex: 1 1 auto;
      overflow: auto;
      padding-top: 2px;
    }

    #${PANEL_ID} .ytki-output h1,
    #${PANEL_ID} .ytki-output h2,
    #${PANEL_ID} .ytki-output h3,
    #${PANEL_ID} .ytki-output h4,
    #${PANEL_ID} .ytki-output h5,
    #${PANEL_ID} .ytki-output h6 {
      margin: 16px 0 8px;
      color: oklch(16% 0 0);
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0;
      line-height: 1.3;
    }

    #${PANEL_ID} .ytki-output h1:first-child,
    #${PANEL_ID} .ytki-output h2:first-child,
    #${PANEL_ID} .ytki-output h3:first-child {
      margin-top: 0;
    }

    #${PANEL_ID} .ytki-output p {
      margin: 0 0 10px;
    }

    #${PANEL_ID} .ytki-output ul,
    #${PANEL_ID} .ytki-output ol {
      margin: 0 0 12px;
      padding-left: 20px;
    }

    #${PANEL_ID} .ytki-output li {
      margin: 0 0 8px;
    }

    #${PANEL_ID} .ytki-output strong {
      font-weight: 700;
      color: oklch(16% 0 0);
    }

    #${PANEL_ID} .ytki-output blockquote {
      margin: 10px 0 12px;
      padding: 8px 10px;
      border: 1px solid oklch(82% 0 0);
      border-radius: 0;
      background: oklch(95% 0 0);
      color: oklch(26% 0 0);
    }

    #${PANEL_ID} .ytki-output code {
      border: 1px solid oklch(82% 0 0);
      border-radius: 0;
      padding: 1px 4px;
      background: oklch(94% 0 0);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }

    #${PANEL_ID} .ytki-output a {
      color: oklch(18% 0 0);
      text-decoration: underline;
      text-underline-offset: 2px;
    }

    @media (max-width: 700px) {
      #${PANEL_ID} {
        top: 0;
        right: 0;
        left: 0;
        bottom: 0;
        width: auto;
        height: 100vh;
        border-radius: 0;
      }
    }
  `;

    document.documentElement.appendChild(style);
  }
  document.documentElement.appendChild(panel);

  panel.querySelector(".ytki-close").addEventListener("click", () => panel.remove());

  return panel;
}

async function loadKeyIdeas(panel) {
  const status = panel.querySelector(".ytki-status");
  const output = panel.querySelector(".ytki-output");

  status.textContent = "Extracting transcript and key ideas...";
  output.textContent = "";

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ url: getVideoUrl() }),
    });
    const responseText = await response.text();
    let body;
    try {
      body = JSON.parse(responseText);
    } catch {
      throw new Error(responseText || `Service returned ${response.status}`);
    }

    if (!response.ok || !body.ok) {
      throw new Error(body.error || `Request failed (${response.status})`);
    }

    output.innerHTML = renderMarkdown(body.keyIdeas);
    status.textContent = body.title || "Done";
  } catch (e) {
    status.textContent = e.message;
  }
}

function togglePanel() {
  const existing = document.getElementById(PANEL_ID);
  if (existing) {
    existing.remove();
    return;
  }

  const panel = createPanel();
  loadKeyIdeas(panel);
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "TOGGLE_KEY_IDEAS_PANEL") {
    togglePanel();
  }
});
})();
