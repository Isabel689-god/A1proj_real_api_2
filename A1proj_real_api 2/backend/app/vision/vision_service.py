"""故障图片视觉理解：调用通义千问多模态 API（OpenAI 兼容接口）。"""

import base64
import mimetypes
from pathlib import Path

from openai import OpenAI

from app.core.config import get_settings


class VisionService:
    """将故障图片转为文本描述，供语义检索与故障定位。"""

    PROMPT = (
        '分析这张工业设备故障图片，严格按以下格式输出，禁止开场白：\n'
        '故障代码:（图片中的数字/字母报警码，如176、HM31等，没有则写无）\n'
        '故障描述:（一句话描述画面内容）\n'
        '关键词:（逗号分隔，优先报警码数字，再是设备/部件名）'
    )

    def __init__(self):
        settings = get_settings()
        key = settings.vision_api_key
        base = settings.vision_api_base
        if not key:
            raise ValueError("未配置 API Key，无法调用视觉模型。")
        self._client = OpenAI(api_key=key, base_url=base)
        self.model = settings.VISION_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        # 通义 qwen-vl-plus 模型暂不支持 streaming，用非流式调用
        self._streaming = False

    def _call_multimodal(self, image_url: str) -> str:
        """通过 OpenAI 兼容接口调用多模态模型。image_url 可以是 http(s) 或 data URL。"""
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": self.PROMPT},
                    ],
                }
            ],
            temperature=0.2,
            max_tokens=800,
            timeout=self.timeout,
        )
        return resp.choices[0].message.content.strip()

    @staticmethod
    def _to_data_url(image_bytes: bytes, mime: str) -> str:
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        return f"data:{mime};base64,{b64}"

    def analyze_image_bytes(self, image_bytes: bytes, mime: str = "image/jpeg") -> dict:
        data_url = self._to_data_url(image_bytes, mime)
        description = self._call_multimodal(data_url)
        keywords = self._extract_keywords(description)
        return {
            "description": description,
            "keywords": keywords,
            "search_query": f"{description}\n关键词：{', '.join(keywords)}",
        }

    def analyze_image_path(self, path: str | Path) -> dict:
        path = Path(path)
        mime, _ = mimetypes.guess_type(str(path))
        mime = mime or "image/jpeg"
        return self.analyze_image_bytes(path.read_bytes(), mime=mime)

    def analyze_image_url(self, image_url: str) -> dict:
        """支持 http(s) 图片 URL 或 data URL（base64 data URL）。"""
        description = self._call_multimodal(image_url)
        keywords = self._extract_keywords(description)
        return {
            "description": description,
            "keywords": keywords,
            "search_query": f"{description}\n关键词：{', '.join(keywords)}",
        }

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        import re

        # 从"故障代码"行提取报警码
        code_match = re.search(r"故障代码[：:]\s*(\S+)", text)
        # 从"关键词"行提取关键词
        kw_match = re.search(r"关键词[：:]\s*(.+)$", text, re.MULTILINE)
        if kw_match:
            parts = re.split(r"[,，、\s]+", kw_match.group(1).strip())
            result = [p for p in parts if p][:12]
            # 故障代码优先插入
            if code_match:
                code = code_match.group(1).strip()
                if code and code != "无" and code not in result:
                    result.insert(0, code)
            return result
        # 回退：提取中文词 + 数字/字母代码（如"176"、"HM31"）
        candidates = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,8}", text)
        # 去重但保留顺序，优先保留含数字的（可能是故障代码）
        seen: set[str] = set()
        result: list[str] = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                result.append(c)
        # 把含数字的排前面（故障代码优先）
        result.sort(key=lambda x: (0 if any(ch.isdigit() for ch in x) else 1))
        return result[:12]
