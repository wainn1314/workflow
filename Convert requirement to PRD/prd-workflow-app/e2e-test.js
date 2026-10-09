'use strict';
const { spawn } = require('child_process');

const child = spawn(process.execPath, ['server.js'], {
  cwd: __dirname,
  env: { ...process.env, PORT: '3998' },
});
let out = '';
child.stdout.on('data', (d) => { out += d; });
child.stderr.on('data', (d) => { out += d; });

const BASE = 'http://localhost:3998';
const inputs = {
  feature_name: '员工请假审批系统',
  user_scenario: '员工在手机上发起请假申请，选择请假类型、填写请假时间和事由后提交；由直属主管在线审批；审批通过后自动通知人事与财务，员工可实时查看审批进度。',
  core_pain_point: '目前请假依赖纸质单据和口头申请，审批流程不透明，员工无法实时查看进度，人事需手工统计考勤，容易遗漏、出错且耗时。',
  mvp_scope: '第一版包含：请假申请提交、主管审批、审批记录查看、审批结果通知、我的请假记录列表。',
  non_functional_requirements: '需支持移动端访问，接口响应时间小于 2 秒，请假数据加密存储并保留审计日志，其余无特殊要求。',
};

async function waitForServer() {
  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch(BASE + '/api/records');
      if (r.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error('server not up: ' + out);
}

(async () => {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), 900000);
  let recordId = null;
  try {
    await waitForServer();
    console.log('服务已启动，开始生成 PRD ...');

    const resp = await fetch(BASE + '/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(inputs),
      signal: ac.signal,
    });
    console.log('generate 响应状态:', resp.status);

    if (!resp.ok) {
      console.log('响应体:', await resp.text());
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep;
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        let event = 'message';
        let dataStr = '';
        for (const line of raw.split('\n')) {
          const l = line.replace(/\r$/, '');
          if (l.startsWith('event:')) event = l.slice(6).trim();
          else if (l.startsWith('data:')) dataStr += l.slice(5).trim();
        }
        let data = {};
        try { data = JSON.parse(dataStr); } catch {}
        if (event === 'record_created') recordId = data.id;
        if (event === 'progress') console.log('  [进度]', data.event, data.title, data.status || '');
        if (event === 'done') {
          console.log('  [完成] status =', data.status, '| PRD 长度 =', (data.final_prd || '').length, '| 耗时 =', data.elapsed_time, 's');
          console.log('  [PRD 前 300 字] >>>');
          console.log((data.final_prd || '').slice(0, 300));
        }
        if (event === 'error') console.log('  [错误]', data.message);
      }
    }
  } catch (e) {
    if (e && e.name === 'AbortError') console.log('  测试超时（180s）未完成');
    else console.error('E2E FAIL:', e && e.message ? e.message : e, '\n服务器日志：', out);
  } finally {
    clearTimeout(timer);
  }

  if (recordId) {
    try {
      const d = await fetch(BASE + '/api/download/' + recordId);
      console.log('下载接口 ->', d.status, '| Content-Disposition:', d.headers.get('content-disposition'));
      const text = await d.text();
      console.log('下载内容长度:', text.length);
    } catch (e) {
      console.error('下载测试失败:', e.message);
    }
  }

  child.kill();
  process.exit(0);
})();
