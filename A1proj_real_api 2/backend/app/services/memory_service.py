"""用户长期记忆服务 — LLM 驱动的知识压缩。

每个用户存储为 compact 事实列表，由 LLM 决定什么值得记住。
每次对话后调 LLM 从 Q&A 中提取关键事实，注入下轮 system prompt。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import get_settings
from app.core.llm_provider import get_llm

_MAX_FACTS = 40
_MAX_FACT_LEN = 80

_EXTRACT_PROMPT = """你是一个知识压缩器。从下面这段维修对话中提取 0-3 条值得记住的关键事实。

规则：
1. 只记住未来会有用的事实——用户偏好、设备型号、故障名称+方案、纠正的信息
2. 忽略临时闲聊、打招呼、纯粹道谢
3. 每条事实 ≤ 40 字，用中文
4. 输出严格 JSON 数组，如：["事实1","事实2"]
5. 如果没什么值得记的，输出空数组 []

对话：
用户：{question}
系统：{answer}"""


class UserMemoryService:
    def __init__(self):
        settings = get_settings()
        self._path = Path(settings.KNOWLEDGE_DIR) / "user_memory.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm(temperature=0.1, max_tokens=512)
        return self._llm

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save(self, data: dict):
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ═══════════ 公开接口 ═══════════

    def get_memory_text(self, user_id: str) -> str:
        """获取用户记忆摘要，注入 system prompt。"""
        mem = self._load().get(user_id)
        if not mem:
            return ""
        facts = mem.get("facts", [])
        if not facts:
            return ""
        return (
            "【该用户的历史知识】\n"
            + "\n".join(f"  · {f}" for f in facts[-_MAX_FACTS:])
            + "\n\n回答时参考以上信息，避免重复已尝试的方案，优先匹配用户常用设备。"
        )

    def update_from_conversation(
        self,
        user_id: str,
        question: str,
        answer: str,
        device_model: str | None = None,
    ) -> None:
        """LLM 从本轮对话中提取关键事实，更新记忆。"""
        # 构建 prompt
        q = question[:800]
        a = answer[:1200]
        prompt = _EXTRACT_PROMPT.format(question=q, answer=a)

        new_facts: list[str] = []
        try:
            resp = self.llm.invoke([
                SystemMessage(content="你是一个知识压缩器，输出严格 JSON 数组。"),
                HumanMessage(content=prompt),
            ])
            raw = resp.content if hasattr(resp, "content") else str(resp)
            # 提取 JSON 数组
            import re
            match = re.search(r"\[[\s\S]*\]", raw)
            if match:
                new_facts = json.loads(match.group(0))
                if not isinstance(new_facts, list):
                    new_facts = []
        except Exception:
            return

        # 过滤 + 去重
        new_facts = [f.strip()[: _MAX_FACT_LEN] for f in new_facts if f and isinstance(f, str) and len(f.strip()) >= 3]
        if not new_facts:
            return

        data = self._load()
        mem = data.get(user_id, {})
        existing = mem.get("facts", [])
        for f in new_facts:
            if f not in existing:
                existing.append(f)
        # 保留最近 40 条
        mem["facts"] = existing[-_MAX_FACTS:]
        mem["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        data[user_id] = mem
        self._save(data)


memory_service = UserMemoryService()
