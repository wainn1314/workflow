'use strict';
const { spawn } = require('child_process');

const child = spawn(process.execPath, ['server.js'], {
  cwd: __dirname,
  env: { ...process.env, PORT: '3999' },
});

let out = '';
child.stdout.on('data', (d) => { out += d; });
child.stderr.on('data', (d) => { out += d; });

const BASE = 'http://localhost:3999';

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
  try {
    await waitForServer();
    console.log('启动日志：', out.trim().split('\n').slice(-3).join(' | '));

    let r = await fetch(BASE + '/api/records');
    console.log('GET /api/records ->', r.status, JSON.stringify(await r.json()));

    r = await fetch(BASE + '/');
    const html = await r.text();
    console.log('GET / ->', r.status, '含标题:', html.includes('需求 PRD 自动生成'));

    r = await fetch(BASE + '/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
    console.log('POST /api/generate(空) ->', r.status, JSON.stringify(await r.json()));

    r = await fetch(BASE + '/api/download/999');
    console.log('GET /api/download/999 ->', r.status, JSON.stringify(await r.json()));

    r = await fetch(BASE + '/api/records/999');
    console.log('GET /api/records/999 ->', r.status, JSON.stringify(await r.json()));
  } catch (e) {
    console.error('SMOKE FAIL:', e && e.message ? e.message : e);
  } finally {
    child.kill();
    process.exit(0);
  }
})();
