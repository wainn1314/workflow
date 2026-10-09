// ===== 本地配置模板（可安全入库）=====
// 用法：复制本文件为 config.js 后填写真实值
//   Windows:      copy config.example.js config.js
//   macOS/Linux:  cp config.example.js config.js
// config.js 已被根级 .gitignore 忽略，绝不入库；本模板只是占位符，不含真实密钥。
//
// 也可以完全不创建 config.js：页面首次点击「生成」时会提示你输入 API Key，
// 只保存在本机浏览器 localStorage，同样不会入库。
window.DIFY_CONFIG = {
  baseUrl: 'https://api.dify.ai/v1',
  apiKey: 'app-REPLACE_WITH_YOUR_DIFY_APP_KEY'
};
