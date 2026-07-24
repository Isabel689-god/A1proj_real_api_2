"""对 数控机床.pdf 的文档块进行 LLM 三元组抽取。结果同时写 MySQL 和 JSON 兜底。"""
import json, sys, time, logging, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('extract-cnc')

from app.pipeline.extractor import TripleExtractor
from app.pipeline.validator import TripleValidator, Triple
from app.pipeline.deduper import TripleDeduper
from app.knowledge.sync_service import KnowledgeSyncService
from app.langchain.rag_chain import _mk_llm
from app.pipeline.prompts import TRIPLE_EXTRACTION_PROMPT_COMPACT
from app.db.engine import init_db
from app.pipeline.db_writer import TripleDBWriter


OUTPUT_DIR = Path(__file__).resolve().parent
STATE_FILE = OUTPUT_DIR / "cnc_extraction_state.json"
TRIPLES_FILE = OUTPUT_DIR / "cnc_triples.json"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text('utf-8'))
    return {"processed_batches": 0, "total_triples": 0, "errors": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), 'utf-8')


def save_triples(triples: list[Triple]):
    """追加三元组到 JSON 文件。"""
    existing = []
    if TRIPLES_FILE.exists():
        existing = json.loads(TRIPLES_FILE.read_text('utf-8'))
    for t in triples:
        existing.append({
            "head_type": t.head_type, "head_name": t.head_name,
            "relation": t.relation,
            "tail_type": t.tail_type, "tail_name": t.tail_name,
        })
    TRIPLES_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), 'utf-8')


def extract_and_save(docs: list[dict], batch_size: int = 10):
    """逐个 batch 抽取，即时保存状态。"""
    llm = _mk_llm(temperature=0.1, streaming=False)
    validator = TripleValidator()
    deduper = TripleDeduper()

    state = load_state()
    start_batch = state["processed_batches"]
    all_triples: list[Triple] = []

    num_batches = (len(docs) + batch_size - 1) // batch_size
    logger.info(f"总文档: {len(docs)}, batch_size={batch_size}, 总 batch 数: {num_batches}")
    logger.info(f"从 batch {start_batch} 开始...")

    for bi in range(start_batch, num_batches):
        batch = docs[bi * batch_size : (bi + 1) * batch_size]
        text = "\n---\n".join(
            f"[{d['id']}] {d.get('title', '')}: {d.get('content', '')}"
            for d in batch
        )
        prompt = TRIPLE_EXTRACTION_PROMPT_COMPACT.format(document_text=text[:3000])

        t0 = time.time()
        try:
            raw = llm.invoke(prompt)
            elapsed = time.time() - t0
            content = raw.content if hasattr(raw, 'content') else str(raw)

            # 解析三元组
            parsed = []
            for line in content.strip().split("\n"):
                line = line.strip()
                if not line or line.count('|') < 4:
                    continue
                parts = line.split("|")
                if len(parts) >= 5:
                    parsed.append(Triple(
                        head_type=parts[0].strip(), head_name=parts[1].strip(),
                        relation=parts[2].strip(),
                        tail_type=parts[3].strip(), tail_name=parts[4].strip(),
                    ))
                    parsed[-1].source_doc = batch[0].get('source', '数控机床.pdf')
                    parsed[-1].confidence = 0.7

            logger.info(f"[{bi+1}/{num_batches}] {len(batch)} 文档 → {len(parsed)} 三元组 ({elapsed:.1f}s)")

            # 校验 + 消重
            valid, _ = validator.validate(parsed)
            unique = deduper.dedup(valid)
            all_triples.extend(unique)

            # 实时保存 JSON
            save_triples(unique)

            # 更新状态
            state["processed_batches"] = bi + 1
            state["total_triples"] += len(unique)
            save_state(state)

        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"[{bi+1}/{num_batches}] 失败 ({elapsed:.1f}s): {e}")
            state["errors"].append(f"batch {bi}: {str(e)[:200]}")
            save_state(state)

    logger.info(f"抽取完成! 总三元组: {len(all_triples)}")
    return all_triples


def write_to_mysql(triples: list[Triple]):
    """尝试写入 MySQL，失败不阻塞。"""
    try:
        init_db()
        writer = TripleDBWriter()
        stats = writer.insert_batch(triples)
        logger.info(f"MySQL 写入: 实体+{stats['entities_inserted']}, 关系+{stats['relations_inserted']}")
        return stats
    except Exception as e:
        logger.warning(f"MySQL 写入失败（三元组已保存 JSON）: {e}")
        return {}


def main():
    svc = KnowledgeSyncService()
    all_docs = svc.load_all_documents()
    cnc_docs = [d for d in all_docs if d.get('source', '') == '数控机床.pdf']

    keywords = ['故障', '报警', '解决', '原因', '更换', '参数', '主轴', '伺服', '诊断', '维修']
    useful = [d for d in cnc_docs if len(d.get('content', '')) > 200
              and sum(1 for kw in keywords if kw in d.get('content', '')) >= 2]
    logger.info(f"数控机床.pdf: {len(useful)} 有效块 / {len(cnc_docs)} 总块")

    # Phase 1: LLM 抽取 → JSON
    triples = extract_and_save(useful, batch_size=10)

    # Phase 2: 尝试 MySQL
    if triples:
        write_to_mysql(triples)

    # 打印汇总
    logger.info("=" * 60)
    logger.info(f"总三元组: {len(triples)}")
    logger.info(f"JSON 备份: {TRIPLES_FILE}")
    logger.info(f"状态文件: {STATE_FILE}")


if __name__ == '__main__':
    main()
