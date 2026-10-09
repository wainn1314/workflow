/* AI 应用评测流水线 - 前端逻辑 */
const DIMS = [
  { key: 'factuality', label: '事实准确性' },
  { key: 'hallucination', label: '幻觉率' },
  { key: 'instruction_following', label: '指令遵循度' },
  { key: 'completeness', label: '完整性' },
  { key: 'safety', label: '安全合规' },
];

let currentRunId = null;
let pollTimer = null;
let logSeq = 0;
const charts = {};

const $ = (id) => document.getElementById(id);

function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function fmtNum(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '-';
  return Number(v).toFixed(digits);
}

function fmtPct(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '-';
  return (Number(v) * 100).toFixed(1) + '%';
}

function toast(msg, type = '') {
  const t = $('toast');
  t.textContent = msg;
  t.className = 'toast ' + type;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add('hidden'), 2600);
}

async function api(url, opts = {}) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    let msg = 'HTTP ' + res.status;
    try { const j = await res.json(); if (j && j.detail) msg = j.detail; } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

function loadConfig() {
  try {
    const c = JSON.parse(localStorage.getItem('evalConfig') || '{}');
    $('modelBaseUrl').value = c.modelBaseUrl || '';
    $('modelName').value = c.modelName || '';
    $('modelApiKey').value = c.modelApiKey || '';
    $('modelProvider').value = c.modelProvider || '';
    $('modelWorkflowInputs').value = c.modelWorkflowInputs || '';
    $('modelMock').checked = c.modelMock !== false;
    $('judgeBaseUrl').value = c.judgeBaseUrl || '';
    $('judgeName').value = c.judgeName || '';
    $('judgeApiKey').value = c.judgeApiKey || '';
    $('judgeProvider').value = c.judgeProvider || '';
    $('judgeMock').checked = c.judgeMock !== false;
    $('concurrency').value = c.concurrency || 5;
    $('maxRetries').value = c.maxRetries || 3;
    $('timeout').value = c.timeout || 120;
    $('temperature').value = c.temperature || 0;
    $('judgeTemperature').value = c.judgeTemperature || 0;
    $('stream').checked = c.stream !== false;
  } catch (e) {}
}

function saveConfig() {
  localStorage.setItem('evalConfig', JSON.stringify({
    modelBaseUrl: $('modelBaseUrl').value, modelName: $('modelName').value, modelApiKey: $('modelApiKey').value,
    modelProvider: $('modelProvider').value, modelMock: $('modelMock').checked,
    modelWorkflowInputs: $('modelWorkflowInputs').value,
    judgeBaseUrl: $('judgeBaseUrl').value, judgeName: $('judgeName').value, judgeApiKey: $('judgeApiKey').value,
    judgeProvider: $('judgeProvider').value, judgeMock: $('judgeMock').checked,
    concurrency: $('concurrency').value, maxRetries: $('maxRetries').value, timeout: $('timeout').value,
    temperature: $('temperature').value, judgeTemperature: $('judgeTemperature').value, stream: $('stream').checked,
  }));
}

function parseWorkflowInputs() {
  const raw = ($('modelWorkflowInputs')?.value || '').trim();
  if (!raw) return {};
  try {
    const obj = JSON.parse(raw);
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) throw new Error('必须是 JSON 对象');
    return obj;
  } catch (e) {
    toast('工作流输入变量不是合法 JSON：' + e.message, 'error');
    return undefined;
  }
}

async function refreshRuns() {
  const runs = await api('/api/runs');
  const sel = $('runSelect');
  const prev = currentRunId || sel.value;
  sel.innerHTML = '<option value="">-- 选择评测 --</option>';
  runs.forEach(r => {
    const c = r._counts || {};
    const opt = document.createElement('option');
    opt.value = r.id;
    opt.textContent = `#${r.id} ${r.name} [${r.status}] (${c.success || 0}/${c.total || 0})`;
    sel.appendChild(opt);
  });
  if (prev) { sel.value = prev; currentRunId = prev; }
  else if (runs.length) { sel.value = runs[0].id; currentRunId = runs[0].id; }
}

function onRunChange(id) {
  currentRunId = id ? Number(id) : null;
  stopPolling();
  logSeq = 0;
  $('logPanel').innerHTML = '';
  $('progressBar').style.width = '0';
  $('progressText').textContent = '空闲';
  if (currentRunId) {
    loadReport();
    loadReview();
    startPolling();
  }
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + name));
  if (name === 'report') loadReport();
  if (name === 'review') loadReview();
  if (name === 'history') loadHistory();
}

async function startRun() {
  const file = $('fileInput').files[0];
  if (!file) { toast('请先选择测试集文件', 'error'); return; }
  const wfInputs = parseWorkflowInputs();
  if (wfInputs === undefined) return;
  saveConfig();
  const config = {
    model: {
      base_url: $('modelBaseUrl').value.trim(),
      api_key: $('modelApiKey').value.trim(),
      model_name: $('modelName').value.trim(),
      provider: $('modelProvider').value,
      mock: $('modelMock').checked,
      workflow_inputs: wfInputs,
    },
    judge: {
      base_url: $('judgeBaseUrl').value.trim(),
      api_key: $('judgeApiKey').value.trim(),
      model_name: $('judgeName').value.trim(),
      provider: $('judgeProvider').value,
      mock: $('judgeMock').checked,
    },
    concurrency: Number($('concurrency').value),
    max_retries: Number($('maxRetries').value),
    timeout_seconds: Number($('timeout').value),
    temperature: Number($('temperature').value),
    judge_temperature: Number($('judgeTemperature').value),
    stream: $('stream').checked,
  };
  const fd = new FormData();
  fd.append('file', file);
  fd.append('config', JSON.stringify(config));
  fd.append('name', file.name);
  try {
    const r = await api('/api/runs', { method: 'POST', body: fd });
    toast('评测任务已创建并开始运行', 'success');
    await refreshRuns();
    currentRunId = r.run_id;
    $('runSelect').value = r.run_id;
    logSeq = 0;
    $('logPanel').innerHTML = '';
    startPolling();
  } catch (e) {
    toast('启动失败：' + e.message, 'error');
  }
}

async function cancelRun() {
  if (!currentRunId) return;
  await api(`/api/runs/${currentRunId}/cancel`, { method: 'POST' });
  toast('已发送取消请求', 'success');
}

async function resumeRun() {
  if (!currentRunId) return;
  await api(`/api/runs/${currentRunId}/resume`, { method: 'POST' });
  toast('已开始断点续跑', 'success');
  logSeq = 0;
  startPolling();
}

function startPolling() {
  stopPolling();
  if (!currentRunId) return;
  pollTimer = setInterval(pollProgress, 1000);
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function pollProgress() {
  if (!currentRunId) return;
  try {
    const p = await api(`/api/runs/${currentRunId}/progress?after_seq=${logSeq}`);
    renderLogs(p.logs || []);
    if (p.last_seq) logSeq = p.last_seq;
    const c = p.counts || {};
    const total = c.total || 0;
    const finished = (c.success || 0) + (c.failed || 0);
    const pct = total ? Math.round(finished / total * 100) : 0;
    $('progressBar').style.width = pct + '%';
    $('progressText').textContent =
      `状态：${p.status} ｜ 成功 ${c.success || 0} / 失败 ${c.failed || 0} / 运行中 ${c.running || 0} / 待处理 ${c.pending || 0} ｜ 进度 ${pct}%`;
    if (p.status === 'completed' || p.status === 'cancelled' || p.status === 'failed') {
      stopPolling();
      await refreshRuns();
      loadReport();
      loadReview();
    }
  } catch (e) {}
}

function renderLogs(logs) {
  const panel = $('logPanel');
  for (const l of logs) {
    const div = document.createElement('div');
    div.className = 'log-line log-' + (l.level || 'info');
    div.textContent = `[${l.ts}] ${l.message}`;
    panel.appendChild(div);
  }
  panel.scrollTop = panel.scrollHeight;
}

async function loadReport() {
  if (!currentRunId) return;
  try {
    const rep = await api(`/api/runs/${currentRunId}/report`);
    renderSummaryCards(rep.overall);
    renderDimTable(rep.overall);
    renderRadarChart(rep.overall);
    renderPassRateChart(rep.by_scenario);
    renderGroupTable($('scenarioTable'), rep.by_scenario, '场景');
    renderGroupTable($('difficultyTable'), rep.by_difficulty, '难度');
  } catch (e) { console.error(e); }
}

function renderSummaryCards(ov) {
  const cards = [
    { k: '总用例数', v: ov.total, cls: '' },
    { k: '通过率', v: fmtPct(ov.pass_rate), cls: (ov.pass_rate || 0) >= 0.8 ? 'green' : 'red' },
    { k: '平均总分', v: fmtNum(ov.avg_total_score), cls: '' },
    { k: '平均延迟(ms)', v: fmtNum(ov.avg_latency_ms, 0), cls: '' },
    { k: '平均首字(ms)', v: fmtNum(ov.avg_ttft_ms, 0), cls: '' },
    { k: '平均总Token', v: fmtNum(ov.avg_total_tokens, 0), cls: '' },
    { k: '成功 / 失败', v: `${ov.success} / ${ov.failed}`, cls: '' },
  ];
  $('summaryCards').innerHTML = cards.map(c =>
    `<div class="stat"><div class="v ${c.cls}">${c.v}</div><div class="k">${c.k}</div></div>`
  ).join('');
}

function renderDimTable(ov) {
  const dims = ov.dims || {};
  let rows = DIMS.map(d =>
    `<tr><td>${d.label}</td><td>${fmtNum(dims[d.key])}</td></tr>`
  ).join('');
  $('dimTable').innerHTML = `<table><thead><tr><th>维度</th><th>平均分</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function destroyChart(name) {
  if (charts[name]) { charts[name].destroy(); delete charts[name]; }
}

function renderRadarChart(ov) {
  destroyChart('radar');
  if (typeof Chart === 'undefined') return;
  const dims = ov.dims || {};
  charts.radar = new Chart($('radarChart'), {
    type: 'radar',
    data: {
      labels: DIMS.map(d => d.label),
      datasets: [{ label: '平均分', data: DIMS.map(d => dims[d.key] ?? 0), fill: true,
        backgroundColor: 'rgba(37,99,235,0.2)', borderColor: '#2563eb', pointBackgroundColor: '#2563eb' }],
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { r: { min: 1, max: 5, ticks: { stepSize: 1 } } } },
  });
}

function renderPassRateChart(groups) {
  destroyChart('pass');
  if (typeof Chart === 'undefined') return;
  charts.pass = new Chart($('passRateChart'), {
    type: 'bar',
    data: {
      labels: groups.map(g => g.group),
      datasets: [{ label: '通过率', data: groups.map(g => (g.pass_rate ?? 0) * 100),
        backgroundColor: '#38bdf8', borderColor: '#0ea5e9', borderWidth: 1 }],
    },
    options: { responsive: true, maintainAspectRatio: false,
      scales: { y: { min: 0, max: 100, ticks: { callback: v => v + '%' } } } },
  });
}

function renderGroupTable(el, groups, groupName) {
  if (!groups.length) { el.innerHTML = '<div class="empty">暂无数据</div>'; return; }
  const head = `<table><thead><tr><th>${groupName}</th><th>总数</th><th>通过率</th><th>平均总分</th><th>平均延迟(ms)</th><th>平均总Token</th></tr></thead>`;
  const body = groups.map(g =>
    `<tr><td>${esc(g.group)}</td><td>${g.total}</td><td>${fmtPct(g.pass_rate)}</td><td>${fmtNum(g.avg_score)}</td><td>${fmtNum(g.avg_latency_ms, 0)}</td><td>${fmtNum(g.avg_total_tokens, 0)}</td></tr>`
  ).join('');
  el.innerHTML = `<div class="table-scroll">${head}<tbody>${body}</tbody></table></div>`;
}

function exportCsv(kind) {
  if (!currentRunId) return;
  window.location.href = `/api/runs/${currentRunId}/export?kind=${kind}`;
}

async function loadReview() {
  if (!currentRunId) return;
  try {
    const rep = await api(`/api/runs/${currentRunId}/report`);
    renderBadcaseList(rep.badcases || []);
  } catch (e) { console.error(e); }
}

function parseJson(s) { try { return JSON.parse(s || '{}'); } catch (e) { return {}; } }

function convText(convJson) {
  const msgs = parseJson(convJson);
  if (Array.isArray(msgs)) return msgs.map(m => `[${m.role}] ${m.content}`).join('\n');
  return '';
}

function renderBadcaseList(badcases) {
  const el = $('badcaseList');
  if (!badcases.length) { el.innerHTML = '<div class="empty">暂无 BadCase</div>'; return; }
  el.innerHTML = badcases.map(r => {
    const judge = parseJson(r.judge_json);
    const scores = parseJson(r.scores_json);
    const reasons = judge.reasons || {};
    const scoreCells = DIMS.map(d =>
      `<div class="score-cell"><div class="dim">${d.label}：${scores[d.key] ?? '-'}</div><div class="reason">${esc(reasons[d.key] || '')}</div></div>`
    ).join('');
    const reviewed = r.human_reviewed ? `<span class="badge-bad">已复核</span>` : '';
    return `<div class="badcase-item" id="bc-${r.id}">
      <div class="badcase-head" onclick="toggleBadcase(${r.id})">
        <span class="title">#${esc(r.ref_id)} · ${esc(r.scenario)} / ${esc(r.difficulty)}</span>
        <span>总分 <b>${fmtNum(r.total_score)}</b></span>
        <span>置信度 ${fmtNum(r.confidence)}</span>
        <span class="${r.passed ? 'badge-pass' : 'badge-fail'}">${r.passed ? '通过' : '不通过'}</span>
        ${reviewed}
        <span style="margin-left:auto">▾</span>
      </div>
      <div class="badcase-body hidden">
        <div class="block"><h4>用户对话</h4><pre>${esc(convText(r.conversation_json))}</pre></div>
        <div class="block"><h4>标准答案</h4><pre>${esc(r.expected_output)}</pre></div>
        <div class="block"><h4>模型输出</h4><pre>${esc(r.actual_output)}</pre></div>
        <div class="block"><h4>各维度评分</h4><div class="score-grid">${scoreCells}</div></div>
        <div class="block"><h4>整体评价</h4><pre>${esc(judge.overall_comment || '')}</pre></div>
        <div class="review-row">
          <button class="btn primary" onclick="saveReview(${r.id}, true)">标记通过</button>
          <button class="btn danger" onclick="saveReview(${r.id}, false)">标记不通过</button>
          <input type="number" id="note-${r.id}" min="1" max="5" step="0.1" placeholder="人工总分(1-5)">
          <input type="text" id="text-${r.id}" placeholder="复核备注" style="flex:1">
          <button class="btn" onclick="saveReview(${r.id}, null)">保存复核</button>
        </div>
      </div>
    </div>`;
  }).join('');
}

function toggleBadcase(id) {
  const body = document.querySelector(`#bc-${id} .badcase-body`);
  if (body) body.classList.toggle('hidden');
}

async function saveReview(id, humanPass) {
  const payload = {
    human_pass: humanPass,
    human_note: $('text-' + id).value || null,
  };
  const scoreEl = $('note-' + id);
  if (scoreEl && scoreEl.value) {
    payload.human_score = Number(scoreEl.value);
  }
  try {
    await api(`/api/results/${id}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    toast('复核已保存', 'success');
    loadReview();
    loadReport();
  } catch (e) {
    toast('保存失败：' + e.message, 'error');
  }
}

async function loadHistory() {
  try {
    const data = await api('/api/history/trend');
    renderTrendChart(data);
    renderHistoryTable(data);
  } catch (e) { console.error(e); }
}

async function deleteRun(id) {
  if (!confirm('确定删除该评测记录？其测试用例、结果与日志将一并删除，且不可恢复。')) return;
  try {
    await api('/api/runs/' + id, { method: 'DELETE' });
    toast('已删除', 'success');
    if (currentRunId === id) {
      currentRunId = null;
      stopPolling();
    }
    refreshRuns();
    loadHistory();
  } catch (e) {
    toast('删除失败：' + e.message, 'error');
  }
}

function renderTrendChart(data) {
  destroyChart('trend');
  if (typeof Chart === 'undefined') return;
  const labels = data.map(d => '#' + d.id + ' ' + (d.name || ''));
  charts.trend = new Chart($('trendChart'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: '通过率(%)', data: data.map(d => (d.pass_rate ?? 0) * 100), borderColor: '#16a34a',
          backgroundColor: 'rgba(22,163,74,0.1)', yAxisID: 'y', tension: 0.3 },
        { label: '平均总分', data: data.map(d => d.avg_score), borderColor: '#2563eb',
          backgroundColor: 'rgba(37,99,235,0.1)', yAxisID: 'y1', tension: 0.3 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        y: { position: 'left', min: 0, max: 100, title: { display: true, text: '通过率%' } },
        y1: { position: 'right', min: 1, max: 5, title: { display: true, text: '平均总分' }, grid: { drawOnChartArea: false } },
      },
    },
  });
}

function renderHistoryTable(data) {
  const el = $('historyTable');
  if (!data.length) { el.innerHTML = '<div class="empty">暂无历史数据</div>'; return; }
  const head = '<table><thead><tr><th>ID</th><th>名称</th><th>时间</th><th>用例数</th><th>通过率</th><th>平均总分</th><th>平均延迟(ms)</th><th>平均总Token</th><th>操作</th></tr></thead>';
  const body = data.map(d =>
    `<tr><td>#${d.id}</td><td>${esc(d.name)}</td><td>${esc(d.created_at)}</td><td>${d.total}</td><td>${fmtPct(d.pass_rate)}</td><td>${fmtNum(d.avg_score)}</td><td>${fmtNum(d.avg_latency_ms, 0)}</td><td>${fmtNum(d.avg_total_tokens, 0)}</td><td><button class="btn danger sm" onclick="deleteRun(${d.id})">删除</button></td></tr>`
  ).join('');
  el.innerHTML = `<div class="table-scroll">${head}<tbody>${body}</tbody></table></div>`;
}

// 初始化
loadConfig();
refreshRuns().then(() => {
  if (currentRunId) {
    loadReport();
    loadReview();
    startPolling();
  }
});





