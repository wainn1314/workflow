# 需求 PRD 自动生成 · 交互前端

一个简单的 Web 前端，接入 Dify「需求PRD自动生成工作流」的 API：

- 输入工作流的 5 个必填参数
- 实时展示工作流各节点执行进度
- 生成完成后预览 PRD，并提供「一键下载」按钮保存为本地 Markdown 文件
- 历史记录存入 SQLite（`node:sqlite`，Node.js 22.5+ 内置，无需额外原生编译）

技术栈：Node.js + Express + SQLite（内置 `node:sqlite`）

## 目录结构

```
prd-workflow-app/
├── server.js          # Express 后端 + Dify 流式代理 + 下载接口
├── db.js              # SQLite 数据访问（记录保存/查询）
├── package.json
├── .env               # 环境配置（含 Dify API Key）
├── .env.example
└── public/
    ├── index.html     # 前端页面
    ├── style.css      # 样式
    └── app.js         # 前端交互逻辑
```

## 快速开始

> 需要 Node.js 22.5+（本项目使用内置 `node:sqlite`）。

```bash
# 1. 进入目录
cd prd-workflow-app

# 2. 安装依赖
npm install

# 3. 确认 .env 配置正确（重点是 DIFY_API_KEY / DIFY_BASE_URL）
#    DIFY_BASE_URL 末尾 /v1 可带可不带，程序会自动兼容：
#    - Dify Cloud 云服务：https://api.dify.ai/v1
#    - 自部署：http://localhost 或 http://你的域名

# 4. 启动
npm start
```

浏览器打开 <http://localhost:3000> 即可使用。

## 配置说明（.env）

| 变量 | 说明 | 示例 |
|---|---|---|
| `DIFY_API_KEY` | Dify 应用 API Key | `app-xxxxxxxx` |
| `DIFY_BASE_URL` | Dify 服务地址（末尾 `/v1` 可带可不带） | `https://api.dify.ai/v1` 或 `http://localhost` |
| `DIFY_USER` | 调用用户标识 | `prd-web-app` |
| `PORT` | 本服务端口 | `3000` |
| `DB_PATH` | SQLite 文件路径（可选） | `./prd.db` |

## 接口说明

- `POST /api/generate` —— 提交 5 个输入，SSE 流式返回进度与结果
- `GET  /api/records` —— 历史记录列表（摘要）
- `GET  /api/records/:id` —— 单条记录详情（含完整 PRD）
- `GET  /api/download/:id` —— 下载 PRD 为 Markdown 文件

## 工作流输入字段

| 变量名 | 标签 | 类型 |
|---|---|---|
| `feature_name` | 功能名称 | 单行文本 |
| `user_scenario` | 用户场景描述 | 段落 |
| `core_pain_point` | 核心痛点 | 段落 |
| `mvp_scope` | MVP范围 | 段落 |
| `non_functional_requirements` | 非功能要求 | 段落 |
