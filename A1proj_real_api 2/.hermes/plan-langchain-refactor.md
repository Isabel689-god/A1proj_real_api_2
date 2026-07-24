# LangChain 重構計劃

## 一、前端 API 端口審計

### ✅ 前端實際使用的端口（必須保留）

| 端口 | 方法 | 來源 | 用途 |
|------|------|------|------|
| `/chat` | POST | `api/chat.ts` | 非流式對話（legacy） |
| `/chat/stream` | POST | `api/chat.ts` | 流式對話 |
| `/chat/stream/multipart` | POST | `api/chat.ts` | 流式對話+圖片 |
| `/user/login` | POST | `LoginView.vue` | 登入 |
| `/user/logout` | POST | `stores/chat.ts` | 登出 |
| `/user/list` | GET | `AdminView.vue` | 用戶列表（admin） |
| `/user/add` | POST | `AdminView.vue` | 新增用戶（admin） |
| `/user/{username}` | DELETE | `AdminView.vue` | 刪除用戶（admin） |
| `/user/{username}/permissions` | PUT | `AdminView.vue` | 更新權限（admin） |
| `/knowledge/manuals` | GET | `AdminView.vue` | 手冊文件列表（admin） |
| `/knowledge/manuals/request` | POST | `ChatSidebar.vue` | 提交手冊上傳申請 |
| `/knowledge/manuals/upload` | POST | `ChatSidebar.vue` | 直接上傳手冊（admin） |
| `/knowledge/manuals/requests` | GET | `AdminView.vue` | 申請列表（admin） |
| `/knowledge/manuals/requests/{id}/review` | POST | `AdminView.vue` | 審核申請（admin） |
| `/knowledge/graph` | GET | `KnowledgeGraph.vue` | 知識圖譜數據 |
| `/knowledge/devices` | GET | `ChatComposer.vue` | 設備型號列表 |
| `/monitor/status` | GET | `AdminView.vue` | 系統狀態（admin） |
| `/monitor/test-llm` | POST | `AdminView.vue` | 測試LLM（admin） |

### ❌ 前端未使用的端口（可刪除）

| 端口 | 原因 |
|------|------|
| `/health` | 前端從不調用 |
| `/retrieve`, `/retrieve/multipart` | 前端用 `/chat/stream` 替代 |
| `/kg/graph`, `/kg/entity`, `/kg/relation`, `/kg/extract` | 前端用 `/knowledge/graph`，不調用 MySQL KG |
| `/knowledge/sync` | 前端標記"待接入" |
| `/knowledge/cases`, `/knowledge/cases/{id}/review` | 前端從不調用 |
| `/knowledge/corrections`, `/knowledge/corrections` POST | 前端從不調用 |
| `/knowledge/graph/query` | 前端從不調用 |
| `/knowledge/manuals/{filename}` DELETE | 前端標記"待接入" |

## 二、文件重構計劃

### Phase 1: 新增 `langchain/` 模組
建立 `backend/app/langchain/`，用 LangChain 標準 API 替代手擼代碼

```
backend/app/langchain/
├── __init__.py
├── embeddings.py   # OpenAIEmbeddings + 自訂 base_url
├── llm.py          # ChatOpenAI + 自訂 base_url（支援串流）
└── vector_store.py # FAISS 向量庫封裝
```

### Phase 2: 簡化 Services + 刪除冗餘檔案

**新增檔案：**
- `backend/app/langchain/`（以上）

**簡化檔案：**
- `backend/app/services/chat_service.py` → 改用 LangChain chain.invoke()
- `backend/app/api/v1/knowledge.py` → 移除未使用的端口
- `backend/app/main.py` → 移除 startup 中的 FAISS 構建

**刪除檔案（整個目錄）：**
- `backend/app/embeddings/` ❌ → 由 `langchain/embeddings.py` 替代
- `backend/app/providers/` ❌ → 由 `langchain/llm.py` 替代
- `backend/app/rag/` ❌ → 由 `langchain/` 模組替代

**刪除檔案（單個）：**
- `backend/app/api/v1/health.py` ❌ → 前端未使用
- `backend/app/api/v1/retrieve.py` ❌ → 前端未使用
- `backend/app/api/v1/kg_api.py` ❌ → 前端未使用（MySQL KG 相關）
- `backend/app/services/retrieval_service.py` ❌ → 由 chat_service 替代
- `backend/app/services/kg_service.py` ❌ → MySQL KG 未使用
- `backend/app/services/kg_extractor.py` ❌ → MySQL KG 未使用

**保留檔案（業務邏輯）：**
- `backend/app/core/config.py` — 配置
- `backend/app/core/logging.py` — 日誌
- `backend/app/knowledge/document_parser.py` — 自訂 PDF/DOCX/XLS 解析
- `backend/app/knowledge/sync_service.py` — 同步協調
- `backend/app/knowledge/dynamic_store.py` — 用戶案例/修正
- `backend/app/knowledge/graph_service.py` — 圖譜查詢（JSON-based）
- `backend/app/knowledge/graph_builder.py` — 圖譜構建
- `backend/app/vision/vision_service.py` — 多模態視覺
- `backend/app/services/user_service.py` — 用戶管理
- `backend/app/db/mysql.py` — MySQL 連線池
- `backend/app/schemas/` — Pydantic schema
- `backend/app/utils/errors.py` — 錯誤工具

### Phase 3: 更新 pyproject.toml

**新增：**
```
langchain>=0.3
langchain-community
langchain-openai
langchain-text-splitters
```

**保留：**
```
fastapi, uvicorn, pydantic, pydantic-settings, python-dotenv
numpy, openai, httpx, python-multipart
faiss-cpu, pypdf, python-docx, pymysql
```

## 三、架構變化

重構前：51 個 Python 檔案，手擼 RAG + Embedding + Provider
重構後：~35 個 Python 檔案，核心 RAG 用 LangChain 標準 API

```
backend/app/
├── main.py                    # FastAPI 入口（精簡）
├── core/
│   ├── config.py              # 不變
│   └── logging.py             # 不變
├── langchain/                 # ✨ NEW
│   ├── __init__.py
│   ├── embeddings.py          # OpenAIEmbeddings(base_url, api_key, model)
│   ├── llm.py                 # ChatOpenAI(model, base_url, api_key, stream)
│   └── vector_store.py        # FAISS save/load/search
├── api/v1/
│   ├── __init__.py
│   ├── chat.py                # 不變（API 層）
│   ├── knowledge.py           # 簡化（移除未使用的端口）
│   ├── monitor.py             # 簡化（移除 providers 依賴）
│   └── user.py                # 不變
├── services/
│   ├── chat_service.py        # ✨ 簡化：調用 langchain chain
│   └── user_service.py        # 不變
├── knowledge/
│   ├── document_parser.py     # 保留（自訂解析）
│   ├── sync_service.py        # 保留（同步邏輯）
│   ├── dynamic_store.py       # 保留（用戶案例）
│   ├── graph_service.py       # 保留（JSON 圖譜查詢）
│   └── graph_builder.py       # 保留（圖譜構建）
├── vision/
│   └── vision_service.py      # 保留（DashScope 多模態）
├── schemas/                   # 保留
└── db/
    └── mysql.py               # 保留（MySQL 連線）
```
