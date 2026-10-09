# Text to File 插件

将文本内容转换为可下载文件的 Dify 插件（用于 PRD 工作流的一键全文下载）。

## 插件标识

| 字段 | 值 |
| --- | --- |
| 插件唯一标识（provider_id） | `prd/text-to-file` |
| provider 名称（provider_name） | `text_to_file` |
| 工具名称（tool_name） | `text_to_file` |
| 工具显示名（tool_label） | `文本转文件` |

## 打包与安装

1. 安装 dify 插件 CLI（如未安装）：
   ```bash
   pip install dify-plugin-cli
   ```
2. 打包插件：
   ```bash
   dify plugin package ./text-to-file-plugin
   ```
   会生成 `text-to-file.difypkg`。
3. 在 Dify 中进入「插件」→「安装本地插件」，上传 `text-to-file.difypkg`。
4. 安装完成后，工具会以「文本转文件」的名称出现在工作流工具列表中。

## 说明

- 该插件不依赖任何外部服务，无需配置凭据。
- 工具参数：
  - `text`（必填，动态参数）：要写入文件的完整文本（例如 PRD 终稿）。
  - `filename`（选填，配置参数）：输出文件名，默认 `PRD.md`，缺少 `.md` 后缀时自动补全。
- 输出：一个可下载的 Markdown 文件（`files` 输出变量）。
