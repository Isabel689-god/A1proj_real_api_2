"""
LangChain LCEL RAG 链 - 数控机床故障诊断知识引擎。

检索: case_search -> vision_augment ->
      (case命中: 跳过后续,直接返回案例上下文) |
      (case未命中: parallel(vector|keyword|code_extract) -> merge -> graph) -> context
生成: LCEL prompt | llm | StrOutputParser (非流式) / prompt | llm (流式)
"""

from __future__ import annotations

import re as _re
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.core.llm_provider import get_llm
from app.knowledge.graph_service import KnowledgeGraphService
from app.knowledge.sync_service import KnowledgeSyncService
from app.langchain.vector_store import DashVectorStore
from app.vision.vision_service import VisionService
from app.services.case_service import case_service


def _mk_llm(temperature: float | None = None, streaming: bool = False):
    return get_llm(temperature=temperature, streaming=streaming)


SYSTEM_PROMPT = (
    "你是数控机床故障诊断专家。请严格按以下格式输出诊断报告。\n\n"
    "使用 ## 标记章节标题，**粗体** 标记关键字段名，- 标记列表项。\n\n"
    "## 一、故障诊断\n"
    "**现象：** 描述故障现象\n"
    "**机型：** 设备型号\n"
    "**报警码：** 报警代码\n\n"
    "## 二、原因分析\n"
    "**直接原因：**\n"
    "- 原因1\n"
    "- 原因2\n"
    "**根本原因：**\n"
    "- 根源\n"
    "**排除项：**\n"
    "- 已排除项及依据\n\n"
    "## 三、解决方案\n"
    "- 步骤1\n"
    "- 步骤2\n"
    "- 步骤3\n\n"
    "## 四、经验总结\n"
    "- 预防措施和类似故障处理思路"
)

# 案例复用 prompt：历史案例优先，手册作为规范验证
CASE_PROMPT = (
    "你是一位数控机床故障诊断专家。以下是历史维修案例，请直接复用该案例的维修方案，"
    "同时参考维修手册中的规范参数，确认安全要求是否准确。\n\n"
    "【历史案例】\n"
    "{case_context}\n\n"
    "【维修手册规范】\n"
    "{manual_context}\n\n"
    "请按以下格式输出：\n"
    "一、案例匹配说明\n"
    "（历史案例与当前问题的匹配情况）\n\n"
    "二、维修方案\n"
    "步骤：\n"
    "1. （步骤1）\n"
    "2. （步骤2）\n\n"
    "三、手册规范补充\n"
    "（案例中未覆盖的安全规范或参数）\n\n"
    "四、经验总结"
)

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "{system_prompt}\n\n【知识库检索结果】\n{context}"),
        (
            "human",
            "【用户问题】\n{question}\n\n严格按上述格式输出，用 ## 标题、**粗体** 字段名、- 列表。",
        ),
    ]
)

CASE_RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "{system_prompt}"),
        (
            "human",
            "【用户问题】\n{question}\n\n严格按上述格式输出，用 ## 标题、**粗体** 字段名、- 列表。",
        ),
    ]
)

STREAM_PROMPT = (
    "数控机床故障诊断专家。用表格输出：\n"
    "一、故障诊断(现象|机型|报警码)->二、原因分析(直接原因|根本原因|排除项)->"
    "三、解决方案(步骤|操作|风险|依据)->四、技术延伸->五、知识溯源。中文，引用原文。"
)

DIAGNOSTIC_MARKERS = {
    "故障设备":     "设备",
    "故障现象":     "现象",
    "故障分析":     "分析",
    "故障排除":     "排除",
    "故障排放":     "排除",
    "经验总结":     "总结",
    "解决方法":     "方法",
    "参数":         "参数",
}


def _build_context(docs: list[dict]) -> str:
    if not docs:
        return "（知识库中无相关内容）"
    blocks = []
    total = 0
    for idx, doc in enumerate(docs, start=1):
        content = doc.get("content", "")
        content = _re.sub(r"[^\u4e00-\u9fff\u3000-\u303fa-zA-Z0-9\s]+", " ", content)
        content = _re.sub(r"\s+", " ", content).strip()
        score = doc.get("score", 0)
        source = doc.get("source", "knowledge_base")
        quality = ">90%" if score > 0.4 else (">75%" if score > 0.25 else ">50%")
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
    return "\n\n---\n\n".join(blocks)


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
        if query.lower() in text:
            score += 5.0
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
        d for d in docs
        if dm in f"{d.get('title', '')} {d.get('source', '')} {' '.join(d.get('tags', []))}".lower()
    ]
    return filtered or docs


def _merge_results(*result_lists: list[list[dict]], top_k: int) -> list[dict]:
    merged: dict[str, dict] = {}
    for results in result_lists:
        for doc in results:
            doc_id = doc.get("id") or doc.get("title")
            if doc_id in merged:
                prev = merged[doc_id]
                prev["keyword_score"] = max(prev.get("keyword_score", 0), doc.get("keyword_score", 0))
                prev["vector_score"] = max(prev.get("vector_score", 0), doc.get("vector_score", 0))
                prev["graph_boost"] = max(prev.get("graph_boost", 0), doc.get("graph_boost", 0))
            else:
                merged[doc_id] = dict(doc)
    max_kw = max([d.get("keyword_score", 0) for d in merged.values()] + [1.0])
    out = []
    for doc in merged.values():
        kw = doc.get("keyword_score", 0) / max_kw
        vec = doc.get("vector_score", 0)
        gb = doc.get("graph_boost", 0)
        doc["score"] = round(0.45 * kw + 0.45 * vec + 0.10 * gb, 4)
        out.append(doc)
    out.sort(key=lambda x: x.get("score", 0), reverse=True)
    return out[:top_k]


@dataclass
class RetrievalResult:
    question: str
    search_query: str
    final_docs: list[dict]
    context: str
    vision_result: dict | None = None
    localization: dict | None = None
    case_context: str = ""
    case_matched: bool = False
    manual_context: str = ""


class RAGChain:

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

    # ---- 案例优先检索 ----

    def _stage_case_search(self, inp: dict) -> dict:
        """Step 0: 先查案例库。命中则跳过后续三路检索。"""
        result = case_service.search(
            question=inp["question"],
            device_model=inp.get("device_model"),
            fault_type=None,
        )
        inp["_case_result"] = result
        if result["matched"] and result["cases"]:
            best = result["cases"][0]
            inp["_case_context"] = case_service.format_case_context(best)
            # 交叉验证：找相关手册段落
            fault_keywords = best.get("fault_type", "") + " " + best.get("fault_cause", "")
            if fault_keywords.strip():
                inp["_case_manual_docs"] = keyword_search(
                    fault_keywords, inp["_documents"], 5
                )
            else:
                inp["_case_manual_docs"] = []
        return inp

    # ---- 原有检索阶段 ----

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
            search_query = f"{device_model}\n{search_query}"
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
        vision_result = inp.get("vision_result")
        if vision_result:
            kw_list = vision_result.get("keywords", [])
            if kw_list:
                codes = [k for k in kw_list if any(c.isascii() and c.isalnum() for c in k)]
                if not codes:
                    codes = [k for k in kw_list if len(k) >= 2][:2]
                else:
                    extra = [k for k in kw_list if k in ("报警","故障","代码","错误","异常")]
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
        documents = inp["_documents"]
        top_k = inp["_top_k"]
        question = inp.get("question", "")
        search_query = inp.get("search_query", "")
        codes_text = f"{question} {search_query}"
        query_codes = _re.findall(
            r"(?<![a-zA-Z0-9_])\d{2,4}(?![a-zA-Z0-9_])|[A-Z][A-Z0-9]*\d+", codes_text
        )
        alarm_phrases = _re.findall(r"[A-Z][A-Z\s]{3,}[A-Z]", codes_text.upper())
        if not query_codes and not alarm_phrases:
            return []
        code_query = " ".join(dict.fromkeys(query_codes + alarm_phrases[:2]))
        alarm_words = _re.findall(r"报警|故障|代码|错误|异常|停机|返回|参考|急停|过热|过载", search_query)
        if alarm_words:
            code_query = f"{code_query} {' '.join(alarm_words[:1])}"
        code_results = keyword_search(code_query, documents, top_k * 2)
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
            text_lower = (d.get("title","") + " " + d.get("content","")).lower()
            match_code = any(c in text_lower for c in codes_lower)
            match_phrase = any(p in text_lower for p in phrases_lower if len(p) > 3)
            if not (match_code or match_phrase):
                continue
            full_text = d.get("title","") + " " + d.get("content","")
            near_alarm = False
            for code in query_codes:
                pos = full_text.lower().find(code.lower())
                if pos >= 0:
                    window = full_text[max(0, pos - 80): pos + 80]
                    if alarm_ctx.search(window):
                        near_alarm = True
                        if "报警代码" in window:
                            d["keyword_score"] = d.get("keyword_score", 0) + 5
                        break
            if not near_alarm and not match_phrase:
                continue
            d["keyword_score"] = d.get("keyword_score", 0) + 8
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
        question = inp.get("question", "")
        vision = inp.get("vision_result") or {}
        search_query = inp.get("search_query", "")
        codes_text = f"{question} {search_query}"
        query_codes = _re.findall(r"(?<![a-zA-Z0-9_])\d{2,4}(?![a-zA-Z0-9_])", codes_text)
        has_vision_code = bool(vision.get("keywords"))
        if not query_codes and not has_vision_code:
            return merged
        for doc in merged:
            src = doc.get("source", "")
            if "报警代码及其解析" not in src:
                continue
            content = doc.get("content", "")
            for code in query_codes:
                if f"报警代码：{code}" in content or f"报警 {code}" in content:
                    doc["keyword_score"] = doc.get("keyword_score", 0) + 15
                    break
        return merged

    # ---- 检索主入口 ----

    def retrieve(
        self,
        question: str,
        device_model: str | None = None,
        image_url: str | None = None,
        user_id: str = "",
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

        # Step 0: 案例优先检索
        inp = self._stage_case_search(inp)
        case_result = inp.get("_case_result", {})
        case_matched = case_result.get("matched", False)

        if case_matched:
            # 案例命中：只用手册做交叉验证，不走三路检索
            manual_docs = inp.get("_case_manual_docs", [])
            manual_ctx = _build_context(manual_docs)
            return RetrievalResult(
                question=question,
                search_query=question,
                final_docs=manual_docs,
                context=inp.get("_case_context", ""),
                case_context=inp.get("_case_context", ""),
                case_matched=True,
                manual_context=manual_ctx,
            )

        # 案例未命中：走原有三路检索 + 图谱推理
        inp = self._stage_vision_augment(inp)
        vector_results = self._stage_vector(inp)
        keyword_results = self._stage_keyword(inp)
        code_results = self._stage_code_extract(inp)
        merged = _merge_results(keyword_results, vector_results, top_k=top_k * 2)
        merged = _merge_results(merged, code_results, top_k=top_k * 2)
        merged = _filter_by_device(merged, device_model)
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

    # ---- 生成 ----

    def _gen_chain(self, streaming: bool = False):
        llm = _mk_llm(streaming=streaming)
        if streaming:
            return RAG_PROMPT | llm
        return RAG_PROMPT | llm | StrOutputParser()

    def _gen_case_chain(self, streaming: bool = False):
        llm = _mk_llm(streaming=streaming)
        if streaming:
            return CASE_RAG_PROMPT | llm
        return CASE_RAG_PROMPT | llm | StrOutputParser()

    def generate(self, retrieval: RetrievalResult) -> str:
        import time as _time

        answer = ""
        if retrieval.case_matched:
            params = {
                "system_prompt": CASE_PROMPT.format(
                    case_context=retrieval.case_context[:2000],
                    manual_context=retrieval.manual_context[:1000],
                ),
                "question": retrieval.search_query,
            }
            for attempt in range(3):
                answer = self._gen_case_chain(streaming=False).invoke(params)
                if answer and len(answer.strip()) >= 5:
                    return answer
                if attempt < 2:
                    _time.sleep(1.5 * (attempt + 1))
            return answer

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
                _time.sleep(1.5 * (attempt + 1))
        return answer

    async def agenerate(self, retrieval: RetrievalResult) -> AsyncGenerator[str, None]:
        if retrieval.case_matched:
            chain = self._gen_case_chain(streaming=True)
            params = {
                "system_prompt": CASE_PROMPT.format(
                    case_context=retrieval.case_context[:2000],
                    manual_context=retrieval.manual_context[:1000],
                ),
                "question": retrieval.search_query,
            }
        else:
            chain = self._gen_chain(streaming=True)
            params = {
                "system_prompt": SYSTEM_PROMPT,
                "context": retrieval.context[:600],
                "question": retrieval.search_query,
            }
        async for msg in chain.astream(params):
            if hasattr(msg, "content") and msg.content:
                yield msg.content

    async def astream(self, retrieval: RetrievalResult) -> AsyncGenerator[str, None]:
        async for chunk in self.agenerate(retrieval):
            yield chunk

    def invoke(self, question: str, device_model: str | None = None,
               image_url: str | None = None) -> dict[str, Any]:
        retrieval = self.retrieve(question, device_model, image_url)
        answer = self.generate(retrieval)
        docs = retrieval.final_docs
        result = {
            "answer": answer,
            "sources": [
                {"title": d.get("title"), "source": d.get("source"), "score": d.get("score")}
                for d in docs
            ],
            "confidence": round(max([d.get("score", 0) for d in docs] + [0]), 4),
            "provider": f"langchain:{self.settings.LLM_MODEL}",
            "vision": retrieval.vision_result,
            "fault_localization": retrieval.localization,
        }
        if retrieval.case_matched:
            result["case_matched"] = True
            result["case_context"] = retrieval.case_context[:300]
        return result

    async def astream_tokens(self, question: str, device_model: str | None = None,
                             image_url: str | None = None):
        retrieval = self.retrieve(question, device_model, image_url)
        return retrieval, self.agenerate(retrieval)


rag_chain = RAGChain()
