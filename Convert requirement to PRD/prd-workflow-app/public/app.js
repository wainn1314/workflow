'use strict';

const form = document.getElementById('form');
const submitBtn = document.getElementById('submitBtn');
const resetBtn = document.getElementById('resetBtn');
const progressCard = document.getElementById('progressCard');
const progressList = document.getElementById('progressList');
const resultCard = document.getElementById('resultCard');
const resultContent = document.getElementById('resultContent');
const resultMeta = document.getElementById('resultMeta');
const downloadBtn = document.getElementById('downloadBtn');
const copyBtn = document.getElementById('copyBtn');
const historyList = document.getElementById('historyList');
const refreshBtn = document.getElementById('refreshBtn');

const FIELDS = ['feature_name', 'user_scenario', 'core_pain_point', 'mvp_scope', 'non_functional_requirements'];
const STATUS_TEXT = { running: '生成中', succeeded: '成功', failed: '失败', interrupted: '中断' };

let currentRecordId = null;
let pollTimer = null;
const progressSteps = new Map();

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const inputs = {};
  for (const f of FIELDS) inputs[f] = document.getElementById(f).value.trim();

  const empty = FIELDS.find((f) => !inputs[f]);
  if (empty) {
    alert('请填写所有必填字段后再生成');
    document.getElementById(empty).focus();
    return;
  }
  generate(inputs);
});

resetBtn.addEventListener('click', resetAll);
refreshBtn.addEventListener('click', loadHistory);
copyBtn.addEventListener('click', copyResult);

async function generate(inputs) {
  stopPolling();
  submitBtn.disabled = true;
  submitBtn.textContent = '生成中…';
  progressCard.hidden = false;
  resultCard.hidden = true;
  progressList.innerHTML = '';
  progressSteps.clear();
  currentRecordId = null;
  addProgress('正在连接工作流…', 'running');

  try {
    const resp = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(inputs),
    });

    if (!resp.ok) {
      let msg = `请求失败（${resp.status}）`;
      try {
        const j = await resp.json();
        if (j.error) msg = j.error;
      } catch {}
      throw new Error(msg);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep;
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        handleServerEvent(parseSse(raw));
      }
    }
  } catch (err) {
    showError(err && err.message ? err.message : '生成失败');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = '生成 PRD';
  }
}

function parseSse(raw) {
  let event = 'message';
  let dataStr = '';
  for (const line of raw.split('\n')) {
    const l = line.replace(/\r$/, '');
    if (l.startsWith('event:')) event = l.slice(6).trim();
    else if (l.startsWith('data:')) dataStr += l.slice(5).trim();
  }
  let data = {};
  try { data = JSON.parse(dataStr || '{}'); } catch {}
  return { event, data };
}

function handleServerEvent({ event, data }) {
  switch (event) {
    case 'record_created':
      currentRecordId = data.id;
      markProgress('正在连接工作流…', 'done');
      break;
    case 'progress':
      if (data.event === 'node_started') {
        addProgress(data.title || data.node_type || '处理中', 'running');
      } else if (data.event === 'node_finished') {
        addProgress(data.title || data.node_type || '处理中', data.status === 'succeeded' ? 'done' : 'error');
      }
      break;
    case 'done':
      markAllDone();
      renderResult(data);
      loadHistory();
      break;
    case 'error':
      showError(data.message || '生成失败');
      break;
  }
}

function addProgress(label, status) {
  let step = progressSteps.get(label);
  if (!step) {
    const li = document.createElement('li');
    li.className = 'progress-step';
    const dot = document.createElement('span');
    dot.className = 'dot';
    const labelEl = document.createElement('span');
    labelEl.className = 'step-label';
    labelEl.textContent = label;
    li.appendChild(dot);
    li.appendChild(labelEl);
    progressList.appendChild(li);
    progressSteps.set(label, li);
    step = li;
  }
  step.className = 'progress-step ' + status;
  step.querySelector('.dot').textContent =
    status === 'running' ? '◌' : status === 'done' ? '✓' : '✕';
}

function markProgress(label, status) {
  const step = progressSteps.get(label);
  if (step) {
    step.className = 'progress-step ' + status;
    step.querySelector('.dot').textContent =
      status === 'running' ? '◌' : status === 'done' ? '✓' : '✕';
  } else {
    addProgress(label, status);
  }
}

function markAllDone() {
  for (const step of progressSteps.values()) {
    if (step.classList.contains('running')) {
      step.className = 'progress-step done';
      step.querySelector('.dot').textContent = '✓';
    }
  }
}

function renderResult(data) {
  const prd = data.final_prd || '';
  const isClarify = prd.trim().startsWith('⚠️');
  resultCard.hidden = false;
  resultContent.textContent = prd;
  resultContent.classList.toggle('warning', isClarify);

  if (isClarify) {
    resultMeta.textContent = '⚠️ 输入信息不足，请根据下方提示补充信息后重新生成';
    downloadBtn.hidden = true;
  } else if (data.status === 'succeeded') {
    resultMeta.textContent =
      `生成成功 · 耗时 ${(data.elapsed_time ?? 0).toFixed(1)}s · Token ${data.total_tokens ?? 0}`;
    downloadBtn.hidden = false;
    if (currentRecordId != null) {
      downloadBtn.href = '/api/download/' + currentRecordId;
      downloadBtn.setAttribute('download', '');
    }
  } else {
    resultMeta.textContent = '生成失败';
    downloadBtn.hidden = true;
  }
}

function showError(msg) {
  resultCard.hidden = false;
  resultContent.textContent = msg;
  resultContent.classList.add('warning');
  resultMeta.textContent = '生成失败';
  downloadBtn.hidden = true;
}

async function copyResult() {
  const text = resultContent.textContent || '';
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
  copyBtn.textContent = '已复制';
  setTimeout(() => { copyBtn.textContent = '复制内容'; }, 1500);
}

function resetAll() {
  stopPolling();
  form.reset();
  progressCard.hidden = true;
  resultCard.hidden = true;
  progressList.innerHTML = '';
  progressSteps.clear();
  currentRecordId = null;
  downloadBtn.hidden = true;
  downloadBtn.removeAttribute('href');
}

async function loadHistory() {
  try {
    const resp = await fetch('/api/records');
    if (!resp.ok) return;
    renderHistory(await resp.json());
  } catch {}
}

function renderHistory(records) {
  historyList.innerHTML = '';
  if (!records || !records.length) {
    const li = document.createElement('li');
    li.className = 'empty';
    li.textContent = '暂无记录';
    historyList.appendChild(li);
    return;
  }
  for (const r of records) {
    const li = document.createElement('li');
    li.className = 'history-item clickable';
    li.title = '点击查看详情';

    const title = document.createElement('div');
    title.className = 'history-title';
    title.textContent = r.feature_name;

    const meta = document.createElement('div');
    meta.className = 'history-meta';
    const statusSpan = document.createElement('span');
    statusSpan.className = 'status ' + r.status;
    statusSpan.textContent = STATUS_TEXT[r.status] || r.status;
    meta.appendChild(statusSpan);
    meta.appendChild(document.createTextNode(' · ' + formatTime(r.created_at)));

    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'delete-btn';
    delBtn.title = '删除该记录';
    delBtn.setAttribute('aria-label', '删除该记录');
    delBtn.textContent = '✕';
    delBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteRecord(r.id);
    });

    li.appendChild(title);
    li.appendChild(meta);
    li.appendChild(delBtn);
    li.addEventListener('click', () => loadRecord(r.id));
    historyList.appendChild(li);
  }
}

async function loadRecord(id) {
  try {
    const resp = await fetch('/api/records/' + id);
    if (!resp.ok) return;
    const rec = await resp.json();
    currentRecordId = rec.id;

    if (rec.status === 'running') {
      renderRunningView(rec);
      startPolling(rec.id);
      return;
    }

    stopPolling();
    const prd = rec.final_prd || '';
    const isClarify = prd.trim().startsWith('⚠️');
    resultCard.hidden = false;
    resultContent.textContent = prd;
    resultContent.classList.toggle('warning', isClarify);

    if (isClarify) {
      resultMeta.textContent = '⚠️ 输入信息不足，请根据提示补充信息后重新生成';
      downloadBtn.hidden = true;
    } else if (rec.status === 'succeeded') {
      resultMeta.textContent = '创建于 ' + formatTime(rec.created_at);
      downloadBtn.hidden = false;
      downloadBtn.href = '/api/download/' + rec.id;
      downloadBtn.setAttribute('download', '');
    } else if (rec.status === 'failed') {
      resultMeta.textContent = '生成失败' + (rec.error ? '：' + rec.error : '');
      downloadBtn.hidden = true;
    } else {
      resultMeta.textContent = '生成中断' + (rec.error ? '：' + rec.error : '');
      downloadBtn.hidden = true;
    }
    progressCard.hidden = true;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch {}
}

function renderRunningView(rec) {
  resultCard.hidden = false;
  resultContent.textContent = 'PRD 正在生成中，请稍候…';
  resultContent.classList.remove('warning');
  resultMeta.textContent = '生成中… 正在实时更新进度';
  downloadBtn.hidden = true;

  progressCard.hidden = false;
  progressList.innerHTML = '';
  progressSteps.clear();
  const steps = parseProgress(rec.progress);
  if (steps.length) {
    for (const s of steps) addProgress(s.label, s.status);
  } else {
    addProgress('正在连接工作流…', 'running');
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function startPolling(id) {
  stopPolling();
  pollTimer = setInterval(async () => {
    try {
      const resp = await fetch('/api/records/' + id);
      if (!resp.ok) { stopPolling(); return; }
      const rec = await resp.json();
      if (rec.status === 'running') {
        refreshProgress(rec.progress);
      } else {
        stopPolling();
        loadHistory();
        await loadRecord(id);
      }
    } catch {
      // 网络异常时保持轮询，等待下一次
    }
  }, 3000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function refreshProgress(progressJson) {
  const steps = parseProgress(progressJson);
  if (!steps.length) return;
  progressList.innerHTML = '';
  progressSteps.clear();
  for (const s of steps) addProgress(s.label, s.status);
}

function parseProgress(progressJson) {
  if (!progressJson) return [];
  try {
    const arr = JSON.parse(progressJson);
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

async function deleteRecord(id) {
  if (!confirm('确认删除这条历史记录？此操作不可恢复。')) return;
  try {
    const resp = await fetch('/api/records/' + id, { method: 'DELETE' });
    if (!resp.ok) {
      const j = await resp.json().catch(() => ({}));
      alert(j.error || '删除失败');
      return;
    }
    if (currentRecordId === id) {
      stopPolling();
      resetAll();
    }
    await loadHistory();
  } catch {
    alert('删除失败，请稍后重试');
  }
}

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

loadHistory();
