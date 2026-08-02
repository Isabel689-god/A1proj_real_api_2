"""
LangChain LCEL RAG 链 — 数控机床故障诊断知识引擎。

检索: vision_augment → parallel(vector|keyword|code_extract) → merge → graph → context
生成: LCEL prompt | llm | StrOutputParser (非流式) / prompt | llm (流式)
"""

from __future__ import annotations

import re as _re
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.core.llm_provider import get_llm
from app.knowledge.graph_service import KnowledgeGraphService
from app.knowledge.sync_service import KnowledgeSyncService
from app.langchain.vector_store import DashVectorStore
from app.vision.vision_service import VisionService

# ═══════════════════════════════════════════════════
# LLM 工厂
# ═══════════════════════════════════════════════════


def _mk_llm(temperature: float | None = None, streaming: bool = False):
    return get_llm(temperature=temperature, streaming=streaming)


# ═══════════════════════════════════════════════════
# 诊断型 System Prompt — 故障树引导 + 知识溯源
# ═══════════════════════════════════════════════════

SYSTEM_PROMPT = (
    "一、故障诊断\n\n"
    "\n"
    "现象:\n\n"
    "1. （描述1）\n"
    "2. （描述2）\n"
    "3. （描述3）\n\n"
    "机型:\n\n"
    "\n"
    "报警码:\n\n"
    "\n"
    "\n"
    "二、原因分析\n\n"
    "\n"
    "直接原因:\n\n"
    "1. （原因1）\n"
    "2. （原因2）\n\n"
    "根本原因:\n\n"
    "1. （根源1）\n"
    "2. （根源2）\n\n"
    "排除项:\n\n"
    "1. （排除项1及依据）\n"
    "2. （排除项2及依据）\n\n"
    "\n"
    "\n"
    "三、解决方案\n\n"
    "\n"
    "步骤:\n\n"
    "1. （步骤1）\n"
    "2. （步骤2）\n"
    "3. （步骤3）\n\n"
    "操作:\n\n"
    "\n"
    "风险:\n\n"
    "\n"
    "\n"
    "四、经验总结\n\n"
    "1. （经验1）\n"
    "2. （经验2）\n"
    "3. （经验3）\n"
    "基于解决方案提炼通用经验，包括预防措施和类似故障处理思路。"
)

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "{system_prompt}\n\n【知识库检索结果】\n{context}"),
        (
            "human",
            "【用户问题】\n{question}\n\n直接按上述格式输出，禁止任何开场白、markdown标记、加粗或分隔线。",
        ),
    ]
)

# 流式精简 prompt
STREAM_PROMPT = (
    "数控机床故障诊断专家。用表格输出：\n"
    "一、故障诊断(现象|机型|报警码)→二、原因分析(直接原因|根本原因|排除项)→"
    "三、解决方案(步骤|操作|风险|依据)→四、技术延伸→五、知识溯源。中文，引用原文。"
)

# ═══════════════════════════════════════════════════
# 上下文构建 — 标注诊断字段 + 置信度
# ═══════════════════════════════════════════════════

DIAGNOSTIC_MARKERS = {
    "故障设备": "🛠 设备",
    "故障现象": "👁 现象",
    "故障分析": "🔍 分析",
    "故障排除": "✅ 排除",
    "故障排放": "✅ 排除",  # OCR 常见误识别
    "经验总结": "📋 总结",
    "解决方法": "🔧 方法",
    "参数": "⚙️ 参数",
}


def _build_context(docs: list[dict]) -> str:
    if not docs:
        return "（知识库中无相关内容）"
    blocks = []
    total = 0
    for idx, doc in enumerate(docs, start=1):
        content = doc.get("content", "")
        # 清洗 PDF 乱码：只保留中文/英文/数字/空白
        import re as _re2

        content = _re2.sub(r"[^\u4e00-\u9fff\u3000-\u303fa-zA-Z0-9\s]+", " ", content)
        content = _re2.sub(r"\s+", " ", content).strip()
        score = doc.get("score", 0)
        source = doc.get("source", "knowledge_base")

        # 质量标记
        quality = "★★★★" if score > 0.4 else ("★★★" if score > 0.25 else "★★")
        # 诊断字段标注
        markers = [m for k, m in DIAGNOSTIC_MARKERS.items() if k in content]
        marker_str = " ".join(list(dict.fromkeys(markers))[:4])

        block = (
            f"【资料{idx}】匹配度: {score:.0%} {quality}  {marker_str}\n"
            f"来源: {source}\n"
            f"{content}"
        )
        total += len(block)
        if total > 3000 and blocks:
            break
        blocks.append(block)
    return "\n\n───\n\n".join(blocks)


# ═══════════════════════════════════════════════════
# 关键词搜索 — 含精确匹配加成
# ═══════════════════════════════════════════════════


def keyword_search(query: str, documents: list[dict], top_k: int) -> list[dict]:
    if not query:
        return []
    words = _re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", query.lower())
    bigrams = [
        query[i : i + 2].lower()
        for i in range(max(len(query) - 1, 0))
        if query[i : i + 2].strip()
    ]
    terms = list(dict.fromkeys(words + bigrams))
    results = []
    for doc in documents:
        text = f"{doc.get('title', '')} {doc.get('content', '')} {' '.join(doc.get('tags', []))}".lower()
        score = sum(1.0 for t in terms if t and t in text)
        # 精确短语匹配加成
        if query.lower() in text:
            score += 5.0
        # 连续 bigram 匹配加成
        consecutive = sum(1 for b in bigrams if b in text)
        if consecutive >= 3:
            score += 2.0
        if score > 0:
            item = dict(doc)
            item["keyword_score"] = score
            results.append(item)
    results.sort(key=lambda x: x.get("keyword_score", 0), reverse=True)
    return results[:top_k]


def _filter_by_device(docs: list[dict], device_model: str | None) -> list[dict]:
    if not device_model:
        return docs
    dm = device_model.lower()
    filtered = [
        d
        for d in docs
        if dm
        in f"{d.get('title', '')} {d.get('source', '')} {' '.join(d.get('tags', []))}".lower()
    ]
    return filtered or docs


def _merge_results(*result_lists: list[list[dict]], top_k: int) -> list[dict]:
    """合并多路检索结果，关键词权重提升到 45%，确保精确匹配文档排前。"""
    merged: dict[str, dict] = {}
    for results in result_lists:
        for doc in results:
            doc_id = doc.get("id") or doc.get("title")
            if doc_id in merged:
                prev = merged[doc_id]
                prev["keyword_score"] = max(
                    prev.get("keyword_score", 0), doc.get("keyword_score", 0)
                )
                prev["vector_score"] = max(
                    prev.get("vector_score", 0), doc.get("vector_score", 0)
                )
                prev["graph_boost"] = max(
                    prev.get("graph_boost", 0), doc.get("graph_boost", 0)
                )
            else:
                merged[doc_id] = dict(doc)
    max_kw = max([d.get("keyword_score", 0) for d in merged.values()] + [1.0])
    out = []
    for doc in merged.values():
        kw = doc.get("keyword_score", 0) / max_kw
        vec = doc.get("vector_score", 0)
        gb = doc.get("graph_boost", 0)
        # 权重调整：关键词 45%（精确匹配优先）+ 向量 45% + 图谱 10%
        doc["score"] = round(0.45 * kw + 0.45 * vec + 0.10 * gb, 4)
        out.append(doc)
    out.sort(key=lambda x: x.get("score", 0), reverse=True)
    return out[:top_k]


# ═══════════════════════════════════════════════════
# RetrievalResult
# ═══════════════════════════════════════════════════


@dataclass
class RetrievalResult:
    question: str
    search_query: str
    final_docs: list[dict]
    context: str
    vision_result: dict | None = None
    localization: dict | None = None


# ═══════════════════════════════════════════════════
# RAGChain
# ═══════════════════════════════════════════════════


class RAGChain:
    """数控机床故障诊断 RAG 引擎。"""

    def __init__(self):
        self.settings = get_settings()
        self.sync = KnowledgeSyncService()
        self.vector_store = DashVectorStore()
        self.graph = KnowledgeGraphService()
        self._vision: VisionService | None = None

    @property
    def vision(self) -> VisionService:
        if self._vision is None:
            self._vision = VisionService()
        return self._vision

    # ── 检索阶段 ──

    def _stage_vision_augment(self, inp: dict) -> dict:
        question = inp.get("question", "")
        image_url = inp.get("image_url")
        device_model = inp.get("device_model")
        search_query = question
        vision_result = None
        if image_url:
            try:
                vision_result = self.vision.analyze_image_url(image_url)
                sq = vision_result.get("search_query", "")
                if sq:
                    search_query = f"{question}\n{sq}".strip()
            except Exception as exc:
                vision_result = {"error": str(exc), "description": "", "keywords": []}
        if device_model:
            search_query = f"设备型号：{device_model}\n{search_query}"
        inp["search_query"] = search_query
        inp["vision_result"] = vision_result
        return inp

    def _stage_vector(self, inp: dict) -> list[dict]:
        try:
            return self.vector_store.search(
                inp["search_query"],
                documents=inp["_documents"],
                top_k=inp["_top_k"] * 2,
            )
        except Exception:
            return []

    def _stage_keyword(self, inp: dict) -> list[dict]:
        documents = inp["_documents"]
        top_k = inp["_top_k"]
        question = inp.get("question", "")
        results = keyword_search(question, documents, top_k * 2)
        # 视觉关键词补充
        vision_result = inp.get("vision_result")
        if vision_result:
            kw_list = vision_result.get("keywords", [])
            if kw_list:
                codes = [
                    k for k in kw_list if any(c.isascii() and c.isalnum() for c in k)
                ]
                if not codes:
                    codes = [k for k in kw_list if len(k) >= 2][:2]
                else:
                    extra = [
                        k
                        for k in kw_list
                        if k in ("报警", "故障", "代码", "错误", "异常")
                    ]
                    if extra:
                        codes = codes + extra[:1]
                vq = " ".join(codes)
                if vq.strip():
                    seen_ids = {d.get("id") or d.get("title") for d in results}
                    for d in keyword_search(vq, documents, top_k * 2):
                        did = d.get("id") or d.get("title")
                        if did not in seen_ids:
                            seen_ids.add(did)
                            results.append(d)
        return results

    def _stage_code_extract(self, inp: dict) -> list[dict]:
        """提取报警代码 + 英文短语，精确匹配加权。"""
        documents = inp["_documents"]
        top_k = inp["_top_k"]
        question = inp.get("question", "")
        search_query = inp.get("search_query", "")
        # 数字报警码 — 从问题 + 视觉增强文本中提取
        codes_text = f"{question} {search_query}"
        query_codes = _re.findall(
            r"(?<![a-zA-Z0-9_])\d{2,4}(?![a-zA-Z0-9_])|[A-Z][A-Z0-9]*\d+", codes_text
        )
        # 英文报警短语
        alarm_phrases = _re.findall(r"[A-Z][A-Z\s]{3,}[A-Z]", codes_text.upper())
        if not query_codes and not alarm_phrases:
            return []
        code_query = " ".join(dict.fromkeys(query_codes + alarm_phrases[:2]))
        alarm_words = _re.findall(
            r"报警|故障|代码|错误|异常|停机|返回|参考|急停|过热|过载", search_query
        )
        if alarm_words:
            code_query = f"{code_query} {' '.join(alarm_words[:1])}"
        code_results = keyword_search(code_query, documents, top_k * 2)
        # 补充：直接扫描 XLS 报警代码表，精确匹配的优先加入
        scanned_ids = {d.get("id") or d.get("title") for d in code_results}
        for doc in documents:
            src = doc.get("source", "")
            if "报警代码及其解析" not in src:
                continue
            did = doc.get("id") or doc.get("title")
            if did in scanned_ids:
                continue
            content = doc.get("content", "")
            for code in query_codes:
                if f"报警代码：{code}" in content or f"报警 {code}" in content:
                    d = dict(doc)
                    d["keyword_score"] = 50
                    code_results.insert(0, d)
                    scanned_ids.add(did)
                    break
        codes_lower = {c.lower() for c in query_codes}
        phrases_lower = [p.lower() for p in alarm_phrases]
        out = []
        alarm_ctx = _re.compile(r"报警|故障|错误|异常|代码|停机", _re.IGNORECASE)
        for d in code_results:
            text_lower = (d.get("title", "") + " " + d.get("content", "")).lower()
            match_code = any(c in text_lower for c in codes_lower)
            match_phrase = any(p in text_lower for p in phrases_lower if len(p) > 3)
            if not (match_code or match_phrase):
                continue
            # 代码必须出现在报警上下文附近（100字内），过滤参数号等无关数字
            full_text = d.get("title", "") + " " + d.get("content", "")
            near_alarm = False
            for code in query_codes:
                pos = full_text.lower().find(code.lower())
                if pos >= 0:
                    window = full_text[max(0, pos - 80) : pos + 80]
                    if alarm_ctx.search(window):
                        near_alarm = True
                        # 如果代码紧邻"报警代码"字样，额外加分
                        if "报警代码" in window:
                            d["keyword_score"] = d.get("keyword_score", 0) + 5
                        break
            if not near_alarm and not match_phrase:
                continue
            d["keyword_score"] = d.get("keyword_score", 0) + 8  # +8 精确匹配加成
            out.append(d)
        return out

    def _stage_graph_expand(self, inp: dict) -> list[dict]:
        merged = inp.get("_merged", [])
        documents = inp["_documents"]
        seed_ids = [d.get("id") for d in merged[:3] if d.get("id")]
        expanded_ids = self.graph.expand_doc_ids(seed_ids, limit=5)
        doc_map = {d.get("id"): d for d in documents}
        graph_docs = []
        for eid in expanded_ids:
            if eid in doc_map and eid not in seed_ids:
                gd = dict(doc_map[eid])
                gd["graph_boost"] = 0.6
                graph_docs.append(gd)
        return graph_docs

    def _stage_alarm_code_boost(self, inp: dict, merged: list[dict]) -> list[dict]:
        """图片含故障代码时，优先从报警代码表检索匹配项。"""
        question = inp.get("question", "")
        vision = inp.get("vision_result") or {}
        search_query = inp.get("search_query", "")
        # 从文本中提取数字代码
        codes_text = f"{question} {search_query}"
        query_codes = _re.findall(
            r"(?<![a-zA-Z0-9_])\d{2,4}(?![a-zA-Z0-9_])", codes_text
        )
        has_vision_code = bool(vision.get("keywords"))
        if not query_codes and not has_vision_code:
            return merged
        # 只给包含匹配代码的 XLS 文档加权
        for doc in merged:
            src = doc.get("source", "")
            if "报警代码及其解析" not in src:
                continue
            content = doc.get("content", "")
            # 确认文档内容包含查询中的代码
            for code in query_codes:
                if f"报警代码：{code}" in content or f"报警 {code}" in content:
                    doc["keyword_score"] = doc.get("keyword_score", 0) + 15
                    break
        return merged

    # ── 检索主入口 ──

    def retrieve(
        self,
        question: str,
        device_model: str | None = None,
        image_url: str | None = None,
    ) -> RetrievalResult:
        documents = self.sync.load_all_documents()
        top_k = self.settings.RAG_TOP_K
        inp: dict[str, Any] = {
            "question": question,
            "device_model": device_model,
            "image_url": image_url,
            "_documents": documents,
            "_top_k": top_k,
        }
        inp = self._stage_vision_augment(inp)
        vector_results = self._stage_vector(inp)
        keyword_results = self._stage_keyword(inp)
        code_results = self._stage_code_extract(inp)
        # 合并：关键词优先（精确代码匹配加成高）
        merged = _merge_results(keyword_results, vector_results, top_k=top_k * 2)
        merged = _merge_results(merged, code_results, top_k=top_k * 2)
        merged = _filter_by_device(merged, device_model)
        # 报警代码优先从代码表检索
        merged = self._stage_alarm_code_boost(inp, merged)
        inp["_merged"] = merged
        graph_docs = self._stage_graph_expand(inp)
        final = _merge_results(merged, graph_docs, top_k=top_k)
        localization = None
        if (inp.get("vision_result") or {}).get("keywords"):
            localization = self.graph.fault_localization(
                inp["vision_result"]["keywords"], device_model=device_model
            )
        return RetrievalResult(
            question=question,
            search_query=inp["search_query"],
            final_docs=final,
            context=_build_context(final),
            vision_result=inp.get("vision_result"),
            localization=localization,
        )

    # ── 生成 ──

    def _gen_chain(self, streaming: bool = False):
        llm = _mk_llm(streaming=streaming)
        if streaming:
            return RAG_PROMPT | llm
        return RAG_PROMPT | llm | StrOutputParser()

    def generate(self, retrieval: RetrievalResult) -> str:
        """生成诊断报告，带空回答重试（DashScope 免费额度限速会返回空字符串）。"""
        import time as _time

        params = {
            "system_prompt": SYSTEM_PROMPT,
            "context": retrieval.context[:600],
            "question": retrieval.search_query,
        }
        for attempt in range(3):
            answer = self._gen_chain(streaming=False).invoke(params)
            if answer and len(answer.strip()) >= 5:
                return answer
            if attempt < 2:
                _time.sleep(1.5 * (attempt + 1))  # 指数退避 1.5s / 3s
        return answer  # 最后一次仍空则返回空（由上游降级处理）

    async def agenerate(self, retrieval: RetrievalResult) -> AsyncGenerator[str, None]:
        chain = self._gen_chain(streaming=True)
        async for msg in chain.astream(
            {
                "system_prompt": SYSTEM_PROMPT,
                "context": retrieval.context[:600],
                "question": retrieval.search_query,
            }
        ):
            if hasattr(msg, "content") and msg.content:
                yield msg.content

    async def astream(self, retrieval: RetrievalResult) -> AsyncGenerator[str, None]:
        """流式生成，使用 SYSTEM_PROMPT，供 SSE 端点调用。"""
        async for chunk in self.agenerate(retrieval):
            yield chunk

    # ── 一站式接口 ──

    def invoke(
        self,
        question: str,
        device_model: str | None = None,
        image_url: str | None = None,
    ) -> dict[str, Any]:
        retrieval = self.retrieve(question, device_model, image_url)
        answer = self.generate(retrieval)
        docs = retrieval.final_docs
        return {
            "answer": answer,
            "sources": [
                {
                    "title": d.get("title"),
                    "source": d.get("source"),
                    "score": d.get("score"),
                }
                for d in docs
            ],
            "confidence": round(max([d.get("score", 0) for d in docs] + [0]), 4),
            "provider": f"langchain:{self.settings.LLM_MODEL}",
            "vision": retrieval.vision_result,
            "fault_localization": retrieval.localization,
        }

    async def astream_tokens(
        self,
        question: str,
        device_model: str | None = None,
        image_url: str | None = None,
    ):
        retrieval = self.retrieve(question, device_model, image_url)
        return retrieval, self.agenerate(retrieval)


rag_chain = RAGChain()
