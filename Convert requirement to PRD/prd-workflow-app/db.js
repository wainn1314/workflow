'use strict';

const path = require('path');
const { DatabaseSync } = require('node:sqlite');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'prd.db');
const db = new DatabaseSync(DB_PATH);

db.exec(`
  PRAGMA journal_mode = WAL;
  CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name TEXT NOT NULL,
    user_scenario TEXT NOT NULL,
    core_pain_point TEXT NOT NULL,
    mvp_scope TEXT NOT NULL,
    non_functional_requirements TEXT NOT NULL,
    final_prd TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    error TEXT,
    workflow_run_id TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT,
    progress TEXT
  );
`);

// 兼容旧库：补充 progress 列（用于「生成中」记录展示节点进度）
const cols = db.prepare('PRAGMA table_info(records)').all().map((c) => c.name);
if (!cols.includes('progress')) {
  db.exec('ALTER TABLE records ADD COLUMN progress TEXT');
}

function insertRecord(inputs) {
  const now = new Date().toISOString();
  const result = db
    .prepare(
      `INSERT INTO records
         (feature_name, user_scenario, core_pain_point, mvp_scope, non_functional_requirements, status, created_at)
       VALUES (?, ?, ?, ?, ?, 'running', ?)`
    )
    .run(
      inputs.feature_name,
      inputs.user_scenario,
      inputs.core_pain_point,
      inputs.mvp_scope,
      inputs.non_functional_requirements,
      now
    );
  return Number(result.lastInsertRowid);
}

const ALLOWED_UPDATE_FIELDS = ['final_prd', 'status', 'error', 'workflow_run_id', 'finished_at', 'progress'];

function updateRecord(id, fields) {
  const sets = [];
  const values = [];
  for (const key of ALLOWED_UPDATE_FIELDS) {
    if (key in fields) {
      sets.push(`${key} = ?`);
      values.push(fields[key] ?? null);
    }
  }
  if (!sets.length) return;
  values.push(id);
  db.prepare(`UPDATE records SET ${sets.join(', ')} WHERE id = ?`).run(...values);
}

function getRecord(id) {
  return db.prepare('SELECT * FROM records WHERE id = ?').get(id) || null;
}

function getRecords(limit = 50) {
  return db
    .prepare(
      'SELECT id, feature_name, status, error, created_at, finished_at FROM records ORDER BY id DESC LIMIT ?'
    )
    .all(limit);
}

function deleteRecord(id) {
  db.prepare('DELETE FROM records WHERE id = ?').run(id);
}

module.exports = { insertRecord, updateRecord, getRecord, getRecords, deleteRecord, db };
