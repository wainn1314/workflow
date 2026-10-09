'use strict';

require('dotenv').config();

const path = require('path');
const express = require('express');
const db = require('./db');

const app = express();
app.use(express.json({ limit: '5mb' }));

// 兼容两种写法：https://api.dify.ai 或 https://api.dify.ai/v1（末尾 /v1 会自动去除，避免重复拼接）
const DIFY_BASE_URL = (process.env.DIFY_BASE_URL || 'https://api.dify.ai/v1')
  .replace(/\/+$/, '')
  .replace(/\/v1$/i, '');
const DIFY_WORKFLOW_URL = `${DIFY_BASE_URL}/v1/workflows/run`;
const DIFY_API_KEY = process.env.DIFY_API_KEY || '';
const APP_USER = process.env.DIFY_USER || 'prd-web-app';

// 与 Dify 工作流「开始」节点变量保持一致
const INPUT_FIELDS = [
  { key: 'feature_name', label: '功能名称' },
  { key: 'user_scenario', label: '用户场景描述' },
  { key: 'core_pain_point', label: '核心痛点' },
  { key: 'mvp_scope', label: 'MVP范围' },
  { key: 'non_functional_requirements', label: '非功能要求' },
];

function sse(res, event, data) {
  res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

function safeFilename(name) {
  const cleaned = String(name || 'PRD')
    .replace(/[\\/:*?"<>|\r\n\t]/g, '_')
    .trim();
  return cleaned || 'PRD';
}

// 生成 PRD：流式代理 Dify 工作流，并把进度 / 结果转发给前端
app.post('/api/generate', async (req, res) => {
  const body = req.body || {};
  const missing = INPUT_FIELDS.filter((f) => !String(body[f.key] || '').trim());
  if (missing.length) {
    return res
      .status(400)
      .json({ error: '缺少必填字段：' + missing.map((m) => m.label).join('、') });
  }
  if (!DIFY_API_KEY) {
    return res.status(500).json({ error: '未配置 DIFY_API_KEY，请在 .env 文件中填写' });
  }

  const inputs = {};
  for (const f of INPUT_FIELDS) {
    inputs[f.key] = String(body[f.key]).trim();
  }

  res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();

  const recordId = db.insertRecord(inputs);
  sse(res, 'record_created', { id: recordId });

  const controller = new AbortController();
  res.on('close', () => {
    if (!res.writableEnded) controller.abort();
  });

  // 记录本次工作流的节点进度（持久化到 DB，供「生成中」记录点击查看）
  const progressSteps = new Map();

  function handleEvent(raw) {
    let dataStr = '';
    for (const line of raw.split('\n')) {
      const l = line.replace(/\r$/, '');
      if (l.startsWith('data:')) dataStr += l.slice(5).trim();
    }
    if (!dataStr) return;
    let payload;
    try {
      payload = JSON.parse(dataStr);
    } catch {
      return;
    }

    // Dify 的事件类型位于 data JSON 的 event 字段内（而非 SSE 的 event: 行）
    const eventType = payload.event;

    if (eventType === 'node_started' || eventType === 'node_finished') {
      const d = payload.data || {};
      const title = d.title || d.node_type || '';
      if (title) {
        progressSteps.set(title, {
          label: title,
          status: eventType === 'node_started' ? 'running' : (d.status === 'succeeded' ? 'done' : 'error'),
        });
        db.updateRecord(recordId, { progress: JSON.stringify([...progressSteps.values()]) });
      }
      sse(res, 'progress', {
        event: eventType,
        title: d.title || '',
        node_type: d.node_type || '',
        status: d.status || null,
      });
    } else if (eventType === 'workflow_finished') {
      const d = payload.data || {};
      const outputs = d.outputs || {};
      const finalPrd = typeof outputs.final_prd === 'string' ? outputs.final_prd : '';
      const succeeded = d.status === 'succeeded';
      for (const s of progressSteps.values()) {
        if (s.status === 'running') s.status = succeeded ? 'done' : 'error';
      }
      db.updateRecord(recordId, {
        final_prd: finalPrd,
        status: succeeded ? 'succeeded' : 'failed',
        error: d.error || null,
        workflow_run_id: payload.workflow_run_id || null,
        finished_at: new Date().toISOString(),
        progress: JSON.stringify([...progressSteps.values()]),
      });
      sse(res, 'done', {
        id: recordId,
        status: d.status,
        final_prd: finalPrd,
        elapsed_time: d.elapsed_time,
        total_tokens: d.total_tokens,
      });
    } else if (eventType === 'error') {
      db.updateRecord(recordId, {
        status: 'failed',
        error: payload.message || '工作流执行出错',
        finished_at: new Date().toISOString(),
      });
      sse(res, 'error', { message: payload.message || '工作流执行出错' });
    }
  }

  try {
    const upstream = await fetch(DIFY_WORKFLOW_URL, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${DIFY_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        inputs,
        response_mode: 'streaming',
        user: APP_USER,
      }),
      signal: controller.signal,
    });

    if (!upstream.ok) {
      const errText = await upstream.text();
      throw new Error(`Dify 返回错误（${upstream.status}）：${errText.slice(0, 500)}`);
    }

    const reader = upstream.body.getReader();
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
        handleEvent(raw);
      }
    }
  } catch (err) {
    if (err && err.name === 'AbortError') {
      db.updateRecord(recordId, {
        status: 'interrupted',
        error: '客户端已断开连接',
        finished_at: new Date().toISOString(),
      });
    } else {
      const message = err && err.message ? err.message : '未知错误';
      db.updateRecord(recordId, {
        status: 'failed',
        error: message,
        finished_at: new Date().toISOString(),
      });
      sse(res, 'error', { message });
    }
  } finally {
    res.end();
  }
});

// 历史记录列表（摘要）
app.get('/api/records', (req, res) => {
  res.json(db.getRecords(50));
});

// 单条记录详情（含完整 PRD 文本）
app.get('/api/records/:id', (req, res) => {
  const rec = db.getRecord(Number(req.params.id));
  if (!rec) return res.status(404).json({ error: '记录不存在' });
  res.json(rec);
});

// 删除历史记录
app.delete('/api/records/:id', (req, res) => {
  const rec = db.getRecord(Number(req.params.id));
  if (!rec) return res.status(404).json({ error: '记录不存在' });
  db.deleteRecord(Number(req.params.id));
  res.json({ ok: true });
});

// 下载 PRD 为 Markdown 文件
app.get('/api/download/:id', (req, res) => {
  const rec = db.getRecord(Number(req.params.id));
  if (!rec || !rec.final_prd) return res.status(404).json({ error: 'PRD 内容不存在' });
  const filename = `PRD_${safeFilename(rec.feature_name)}.md`;
  res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
  res.setHeader(
    'Content-Disposition',
    `attachment; filename*=UTF-8''${encodeURIComponent(filename)}`
  );
  res.send(rec.final_prd);
});

// 静态前端资源
app.use(express.static(path.join(__dirname, 'public')));

const PORT = Number(process.env.PORT) || 3000;
app.listen(PORT, () => {
  console.log(`✅ PRD 工作流交互前端已启动：http://localhost:${PORT}`);
  console.log(`   Dify 工作流接口：${DIFY_WORKFLOW_URL}`);
  console.log(`   API Key：${DIFY_API_KEY ? '已配置' : '❌ 未配置（请在 .env 中填写 DIFY_API_KEY）'}`);
});
