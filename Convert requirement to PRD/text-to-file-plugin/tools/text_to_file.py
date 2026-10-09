from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class TextToFileTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        text = tool_parameters.get("text") or ""
        filename = (tool_parameters.get("filename") or "PRD.md").strip()

        if not filename.lower().endswith(".md"):
            filename = f"{filename}.md"

        data = text.encode("utf-8")

        yield self.create_blob_message(
            data,
            meta={
                "filename": filename,
                "mime_type": "text/markdown",
            },
        )
        yield self.create_text_message(f"已生成可下载文件：{filename}（{len(data)} 字节）")
