"use strict";

/* 快速示例：点击后填入文本框 */
const EXAMPLES = {
  ecommerce:
    "我们是一个 5 人的后端小团队，要做一个日活 10 万的电商订单系统：要求高并发写入、" +
    "订单事务强一致、可水平扩展、预算有限；团队熟悉 Python 和 Java。请推荐数据库与后端框架的组合方案。",
  realtime:
    "我们要为 App 做一套实时消息推送系统：峰值 50 万在线连接、消息端到端延迟 200ms 以内、" +
    "需要离线消息与已读回执，团队 8 人、以 Go 和 Java 为主，运维人手很少，托管成本要可控。" +
    "请推荐消息中间件与推送通道的技术方案。",
  analytics:
    "我们每天产生约 2 亿条业务埋点数据，需要做多维分析报表与实时看板，查询要秒级返回，" +
    "团队有 3 名数据工程师、熟悉 SQL 与 Python，预算有限但数据量增长很快。" +
    "请推荐数据仓库与查询引擎方案。",
};

const els = {
  description: document.getElementById("description"),
  charCount: document.getElementById("char-count"),
  submitBtn: document.getElementById("submit-btn"),
  clearBtn: document.getElementById("clear-btn"),
  errorBox: document.getElementById("error-box"),
  healthBadge: document.getElementById("health-badge"),
  healthText: document.getElementById("health-text"),
  reportBody: document.getElementById("report-body"),
  copyBtn: document.getElementById("copy-btn"),
  jsonBtn: document.getElementById("json-btn"),
  jsonView: document.getElementById("json-view"),
  toast: document.getElementById("toast"),
};

let currentReport = null;
let timerId = null;

/* ---------- DOM 构建工具（不使用 innerHTML，避免模型输出造成 XSS） ---------- */
function el(tag, options, children) {
  const opts = options || {};
  const node = document.createElement(tag);
  if (opts.className) node.className = opts.className;
  if (opts.text !== undefined) node.textContent = opts.text;
  if (opts.hidden) node.hidden = true;
  (Array.isArray(children) ? children : [children]).forEach(function (child) {
    if (child) node.appendChild(child);
  });
  return node;
}

function textOrFallback(value, fallback) {
  const text = typeof value === "string" ? value.trim() : "";
  return text || (fallback || "（模型未返回该字段）");
}

function safeList(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map(function (item) {
      if (typeof item === "string") return item.trim();
      return item === null || item === undefined ? "" : String(item);
    })
    .filter(function (item) {
      return item.length > 0;
    });
}

function buildBlock(title, className, content) {
  return el("section", { className: ("block " + (className || "")).trim() }, [
    el("h3", { text: title }),
    content,
  ]);
}

function buildTextList(items, ordered) {
  const list = el(ordered ? "ol" : "ul", { className: ordered ? "alternatives" : "" });
  items.forEach(function (item) {
    list.appendChild(el("li", { text: item }));
  });
  return list;
}

/* ---------- 报告区渲染 ---------- */
function renderEmpty() {
  els.reportBody.replaceChildren(
    el("div", { className: "empty-state" }, [
      el("p", { className: "empty-title", text: "尚未生成报告" }),
      el("p", { className: "hint", text: "在左侧输入业务约束后点击「生成选型报告」。" }),
    ])
  );
}

function renderLoading() {
  const text = el("span", { text: "大模型分析中，请稍候…" });
  const bars = el("div", { className: "skeletons" });
  [92, 100, 78, 88].forEach(function (width) {
    const bar = el("div", { className: "skeleton" });
    bar.style.width = width + "%";
    bars.appendChild(bar);
  });

  els.reportBody.replaceChildren(
    el("div", { className: "tech-card" }, [
      el("span", { className: "label", text: "分析中" }),
      el("div", { className: "loading" }, [el("span", { className: "spinner" }), text]),
    ]),
    bars
  );

  const startedAt = Date.now();
  window.clearInterval(timerId);
  timerId = window.setInterval(function () {
    const seconds = Math.round((Date.now() - startedAt) / 1000);
    text.textContent = "大模型分析中，已等待 " + seconds + " 秒…";
  }, 1000);
}

function stopTimer() {
  window.clearInterval(timerId);
  timerId = null;
}

function renderReport(report) {
  const pros = safeList(report.advantages);
  const cons = safeList(report.disadvantages);
  const alternatives = safeList(report.alternatives);

  const nodes = [
    el("div", { className: "tech-card" }, [
      el("span", { className: "label", text: "推荐方案" }),
      el("p", { className: "tech-name", text: textOrFallback(report.selected_tech) }),
    ]),
    buildBlock("选择理由", "", el("p", { text: textOrFallback(report.reason) })),
  ];

  if (pros.length || cons.length) {
    nodes.push(
      el("div", { className: "grid-2" }, [
        buildBlock(
          "优势",
          "pros",
          pros.length ? buildTextList(pros) : el("p", { className: "hint", text: "模型未给出优势。" })
        ),
        buildBlock(
          "劣势",
          "cons",
          cons.length ? buildTextList(cons) : el("p", { className: "hint", text: "模型未给出劣势。" })
        ),
      ])
    );
  }

  if (alternatives.length) {
    nodes.push(buildBlock("备选方案", "", buildTextList(alternatives, true)));
  }

  els.reportBody.replaceChildren.apply(els.reportBody, nodes);
}

/* ---------- 错误与状态提示 ---------- */
function showError(message) {
  els.errorBox.textContent = message;
  els.errorBox.hidden = false;
}

function hideError() {
  els.errorBox.textContent = "";
  els.errorBox.hidden = true;
}

function formatError(status, data) {
  const detail = data && data.detail;
  if (Array.isArray(detail)) {
    return detail
      .map(function (item) {
        const loc = Array.isArray(item.loc)
          ? item.loc.filter(function (part) { return part !== "body"; }).join(".")
          : "";
        return loc ? loc + "：" + item.msg : String(item.msg);
      })
      .join("\n");
  }
  if (typeof detail === "string" && detail.trim()) return detail;
  const known = {
    422: "入参校验失败（HTTP 422），请检查业务约束描述。",
    500: "服务内部错误（HTTP 500）。",
    502: "大模型调用失败（HTTP 502），请检查网络、API Key 与额度。",
  };
  return known[status] || "请求失败（HTTP " + status + "）。";
}

function setBusy(busy) {
  els.submitBtn.disabled = busy;
  els.submitBtn.textContent = busy ? "分析中…" : "生成选型报告";
  els.copyBtn.disabled = busy;
  els.jsonBtn.disabled = busy;
  els.description.disabled = busy;
}

let toastTimer = null;
function showToast(message) {
  els.toast.textContent = message;
  els.toast.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(function () {
    els.toast.hidden = true;
  }, 2200);
}

/* ---------- 调用工作流 ---------- */
async function submitConstraints() {
  const description = els.description.value.trim();
  if (!description) {
    showError("请先输入业务约束描述，再点击「生成选型报告」。");
    els.description.focus();
    return;
  }

  hideError();
  els.jsonView.hidden = true;
  els.jsonBtn.textContent = "原始 JSON";
  setBusy(true);
  renderLoading();

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description: description }),
    });
    const data = await response.json().catch(function () { return null; });

    if (!response.ok) {
      currentReport = null;
      els.copyBtn.hidden = true;
      els.jsonBtn.hidden = true;
      renderEmpty();
      showError(formatError(response.status, data));
      return;
    }

    currentReport = data;
    renderReport(data);
    els.jsonView.textContent = JSON.stringify(data, null, 2);
    els.copyBtn.hidden = false;
    els.jsonBtn.hidden = false;
    showToast("选型报告已生成");
  } catch (error) {
    currentReport = null;
    els.copyBtn.hidden = true;
    els.jsonBtn.hidden = true;
    renderEmpty();
    showError("请求失败：" + error.message + "。请确认后端服务仍在运行（uvicorn main:app）。");
  } finally {
    stopTimer();
    setBusy(false);
  }
}

/* ---------- 导出 Markdown ---------- */
function toMarkdown(report) {
  const lines = [
    "# 技术选型报告",
    "",
    "## 推荐方案",
    textOrFallback(report.selected_tech),
    "",
    "## 选择理由",
    textOrFallback(report.reason),
    "",
    "## 优势",
  ];
  safeList(report.advantages).forEach(function (item) { lines.push("- " + item); });
  lines.push("", "## 劣势");
  safeList(report.disadvantages).forEach(function (item) { lines.push("- " + item); });
  lines.push("", "## 备选方案");
  safeList(report.alternatives).forEach(function (item, index) {
    lines.push(index + 1 + ". " + item);
  });
  return lines.join("\n");
}

async function copyMarkdown() {
  if (!currentReport) return;
  const text = toMarkdown(currentReport);
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      const helper = document.createElement("textarea");
      helper.value = text;
      helper.setAttribute("readonly", "");
      helper.style.position = "fixed";
      helper.style.opacity = "0";
      document.body.appendChild(helper);
      helper.select();
      document.execCommand("copy");
      document.body.removeChild(helper);
    }
    showToast("已复制 Markdown 报告");
  } catch (error) {
    showToast("复制失败：" + error.message);
  }
}

/* ---------- 健康检查 ---------- */
async function checkHealth() {
  try {
    const response = await fetch("/health", { cache: "no-store" });
    const data = await response.json();
    const ok = response.ok && data && data.status === "ok";
    els.healthBadge.dataset.state = ok ? "ok" : "down";
    els.healthText.textContent = ok ? "服务正常" : "服务异常（HTTP " + response.status + "）";
  } catch (error) {
    els.healthBadge.dataset.state = "down";
    els.healthText.textContent = "无法连接后端";
  }
}

/* ---------- 事件绑定与初始化 ---------- */
function updateCharCount() {
  els.charCount.textContent = String(els.description.value.trim().length);
}

Array.prototype.forEach.call(document.querySelectorAll(".chip[data-example]"), function (chip) {
  chip.addEventListener("click", function () {
    const text = EXAMPLES[chip.dataset.example];
    if (!text) return;
    els.description.value = text;
    updateCharCount();
    hideError();
    els.description.focus();
  });
});

els.submitBtn.addEventListener("click", submitConstraints);
els.copyBtn.addEventListener("click", copyMarkdown);
els.jsonBtn.addEventListener("click", function () {
  const willShow = els.jsonView.hidden;
  els.jsonView.hidden = !willShow;
  els.jsonBtn.textContent = willShow ? "隐藏 JSON" : "原始 JSON";
});

els.clearBtn.addEventListener("click", function () {
  els.description.value = "";
  updateCharCount();
  hideError();
  currentReport = null;
  els.copyBtn.hidden = true;
  els.jsonBtn.hidden = true;
  els.jsonView.hidden = true;
  renderEmpty();
  els.description.focus();
});

els.description.addEventListener("input", function () {
  updateCharCount();
  if (!els.errorBox.hidden) hideError();
});

els.description.addEventListener("keydown", function (event) {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    submitConstraints();
  }
});

renderEmpty();
updateCharCount();
checkHealth();
window.setInterval(checkHealth, 30000);
