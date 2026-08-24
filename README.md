# A1proj 仓库目录说明

本仓库是一套面向 CNC（数控机床）设备的智能故障诊断系统，融合多模态输入（文本 + 图像）、RAG 检索、LangGraph Agent 与知识图谱推理，覆盖从故障提问、SOP 执行到维修归档的闭环。

Git 仓库根目录同时存放：**可运行源码**、**软件工程交付 PDF**、**演示素材**。实际代码在子目录 `A1proj_real_api 2/` 中。

| 项 | 说明 |
|---|---|
| 项目名称 | a1proj-real-api |
| 版本 | 1.0.0 |
| 后端 | FastAPI + LangChain / LangGraph + SQLAlchemy + MySQL |
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Element Plus + ECharts |
| Python | ≥ 3.11（包管理：uv） |
| 默认端口 | 前端 `5173`，后端 `8000` |

---

## 1. 仓库根目录结构

```
A1proj_real_api_2/                          # Git 仓库根
├── README.md                               # 本文件：全库目录与职责说明
├── .gitignore
├── A1proj_real_api 2/                      # 可运行的前后端工程（主代码）
├── doc/                                    # 演示素材
│   ├── intro.pptx
│   ├── introduction1.mp4
│   └── introduction2.mp4
├── 软件功能需求分析文档.pdf
├── 软件功能设计.pdf
├── 软件产品说明书.pdf
├── 软件功能测试报告.pdf
├── 软件部署文档.pdf
└── __MACOSX/                               # macOS 解压残留，可忽略
```

### 1.1 根目录文档对应关系

| 文件 | 角色 |
|---|---|
| `软件功能需求分析文档.pdf` | 需求：场景、功能范围、约束 |
| `软件功能设计.pdf` | 设计：模块划分、接口与数据流 |
| `软件产品说明书.pdf` | 产品说明：面向使用方的功能介绍 |
| `软件功能测试报告.pdf` | 测试：用例与结果 |
| `软件部署文档.pdf` | 部署：环境、启动与上线步骤 |
| `doc/` | 路演 / 介绍用 PPT 与视频 |

---

## 2. 源码工程总览（`A1proj_real_api 2/`）

```
A1proj_real_api 2/
├── backend/                    # FastAPI 后端
├── frontend/                   # Vue 3 前端
├── scripts/                    # 知识库构建与检查脚本
├── data/                       # 维修手册投放目录（PDF/DOCX/XLSX）
├── patent_figures/             # 专利附图目录
├── pyproject.toml / uv.lock    # Python 依赖
├── .env.example                # 环境变量模板（复制为 .env）
├── start.sh                    # Linux 一键启动（路径需按本机修改）
│
├── README.md                   # 后端快速开始
├── README_REAL_API.md          # 真实 API 配置与接口示例
├── ARCHITECTURE.md             # 系统架构（前后端、数据模型、部署）
├── PATENT_CORE_CONTENT.md      # 专利申请核心内容（六阶段 RAG）
├── DEFENSE_DRAFT.md            # 答辩稿
└── LOONGARCH_ADAPTATION.md     # 龙芯 / LoongArch 适配说明
```

系统能力可概括为：**一引擎、双路径、三融合、四闭环**。

- **一引擎**：手册文件 → 解析分块 → JSON 知识库 / JSON 图谱 / MySQL 三元组 / 向量索引。
- **双路径**：案例库优先（置信度 ≥ 0.70 直接复用）→ 手册 RAG + 图谱因果推理兜底。
- **三融合**：向量语义 + 关键词 / 报警代码精确匹配 + 图谱邻居扩展。
- **四闭环**：诊断对话 → SOP 执行 → 维修提报学习 → 记录归档。

---

## 3. 后端（`backend/app/`）

入口：`backend/app/main.py`。启动时幂等建表，并在后台检测 `data/` 手册变更后同步知识库。API 文档：`http://127.0.0.1:8000/docs`。

```
backend/app/
├── main.py                     # FastAPI 入口、CORS、启动钩子
├── api/
│   ├── router.py               # 汇总路由
│   └── v1/
│       ├── chat.py             # 流式对话 / Agent / 会话
│       ├── knowledge.py        # 手册同步、图谱、案例
│       ├── user.py             # 登录、用户与权限组
│       ├── maintenance.py      # 维修记录 CRUD、导出、提报
│       ├── monitor.py          # 运维状态、LLM 探测、模型配置
│       ├── dashboard.py        # 数字大屏概览
│       └── animation.py        # 动画演示生成
├── agent/cnc_agent.py          # LangGraph ReAct Agent（四工具）
├── langchain/
│   ├── rag_chain.py            # 多路融合 RAG
│   ├── vector_store.py         # DashVector 云向量库
│   ├── local_vector_store.py   # FAISS 本地兜底
│   └── dashscope_embeddings.py
├── knowledge/                  # 手册解析、同步、JSON 图谱
├── pipeline/                   # 三元组抽取 → 校验 → 消重 → MySQL
├── services/                   # SOP、会话、用户、案例、图谱 DB
├── vision/vision_service.py    # 故障图像视觉理解
├── db/                         # SQLAlchemy 模型与引擎
└── core/                       # 配置、JWT 鉴权、LLM Provider
```

### 3.1 API 模块

| 前缀 | 职责 |
|---|---|
| `/chat` | SSE 流式问答、`/chat/agent`、会话 CRUD、维修报告状态 |
| `/knowledge` | 手册管理与同步、图谱查询 / 抽取、案例审核 |
| `/user` | 登录登出、用户与权限组 |
| `/maintenance` | 维修记录、CSV 导出、报告同步与提报 |
| `/monitor` | 系统状态、测 LLM、读写模型配置 |
| `/dashboard` | 数字大屏数据 |
| `/animation` | 演示动画生成 |

### 3.2 Agent 工具优先级

`cnc_agent.py` 中检索顺序为：**案例库 → 维修手册 → MySQL 图谱 → SOP 状态**。

| 工具 | 作用 |
|---|---|
| `search_case_library` | 历史维修案例；高置信度可直接复用方案 |
| `search_knowledge_base` | RAG 检索手册切片 |
| `search_mysql_graph` | 故障 → 原因 → 方案因果链 |
| `sop_manage` | 按会话冻结 SOP，只更新步骤状态 |

### 3.3 知识同步流水线

```
data/ 中的 PDF · DOCX · XLS/XLSX
        │
        ▼
  document_parser（扫描版 PDF 可走 OCR）
        │
        ▼
  KnowledgeSyncService.sync()
        ├─ knowledge.json          # 全量文档切片
        ├─ knowledge_graph.json    # 设备-部件-故障 JSON 图谱
        ├─ DashVector / FAISS      # 向量索引
        └─ TripleExtractor         # LLM 抽三元组 → 校验 → 消重 → MySQL
```

---

## 4. 前端（`frontend/src/`）

```
frontend/src/
├── views/
│   ├── LoginView.vue                 # 登录
│   ├── ChatView.vue                  # 主对话（三栏）
│   ├── AdminView.vue                 # 管理端
│   ├── DashboardView.vue             # 数字大屏
│   └── AutomotiveDashboard.vue       # 新能源汽车大屏
├── components/                       # 会话、SOP、图谱、提报、上传等
├── stores/chat.ts                    # Pinia：会话、SOP、鉴权
├── api/chat.ts                       # SSE 流式请求
├── router/index.ts
└── utils/auth.ts                     # JWT + authFetch
```

| 路由 | 页面 | 鉴权 |
|---|---|---|
| `/login` | 登录 | 无 |
| `/chat` | 诊断对话 | 需登录 |
| `/admin` | 管理端 | 管理人员 / 管理组 |
| `/dashboard` | 数字大屏 | 需登录 |
| `/automotive` | 新能源汽车大屏 | 需登录 |

Chat 为三栏布局：左侧会话列表、中间 SSE 消息流、右侧 SOP + 维修报告。管理端覆盖组织权限、手册、案例库、检修记录、知识图谱与系统监控。

---

## 5. 脚本与数据

| 路径 | 说明 |
|---|---|
| `scripts/sync_and_index.py` | 一键：手册同步 + 图谱 + 向量索引 |
| `scripts/build_maintenance_knowledge.py` | 仅构建知识库 |
| `scripts/build_vector_index.py` | 仅构建向量索引 |
| `scripts/check_knowledge.py` | 检查知识库状态 |
| `scripts/test_glm_api.py` | 探测 GLM / OpenAI 兼容接口 |
| `data/` | 投放维修手册；启动时按 MD5 增量同步 |
| `backend/scripts/extract_cnc.py` | CNC 三元组抽取辅助脚本 |

---

## 6. 数据与配置

**MySQL 核心表**（连接信息写在 `.env`，不要提交密钥）：`users`、`sessions`、`messages`、`sys_sop_version`、`sys_maintenance_record`，以及图谱相关的 `fault` / `fault_cause` / `solution` / `relation`、`permission_groups`。

**大模型与检索**（见 `.env.example`）：OpenAI 兼容接口（智谱 / 通义 DashScope 等）、嵌入模型、视觉模型、可选 DashVector；未配置云向量库时回退本地 FAISS。

**鉴权**：JWT（HS256）；管理员接口同时支持 `Authorization: Bearer` 与 `X-Admin-Token`。

---

## 7. 本地启动（简要）

在 `A1proj_real_api 2/` 下：

```bash
cp .env.example .env          # 填写 API Key、MySQL 等
uv sync

# 将 PDF/DOCX/XLSX 放入 data/ 后构建索引
uv run python scripts/sync_and_index.py

# 后端
uv run uvicorn app.main:app --app-dir backend --reload

# 前端（另开终端）
cd frontend && npm install && npm run dev
```

- 前端：http://127.0.0.1:5173  
- 后端 Swagger：http://127.0.0.1:8000/docs  
- 更细的真实 API 示例见 `A1proj_real_api 2/README_REAL_API.md`  
- 龙芯环境见 `A1proj_real_api 2/LOONGARCH_ADAPTATION.md`

`start.sh` 写死了某台 Linux 机器路径，在本仓库直接使用前需要改 `PROJECT_DIR`。

---

## 8. 已有 Markdown 索引

| 文件 | 内容 |
|---|---|
| `A1proj_real_api 2/README.md` | 安装、手册同步、接口速查 |
| `A1proj_real_api 2/README_REAL_API.md` | 真实 Key 配置与 curl 示例 |
| `A1proj_real_api 2/ARCHITECTURE.md` | 架构、目录、SOP、主题、部署 |
| `A1proj_real_api 2/PATENT_CORE_CONTENT.md` | 六阶段多模态 RAG 专利叙述 |
| `A1proj_real_api 2/DEFENSE_DRAFT.md` | 答辩：背景、问题、框架、实现 |
| `A1proj_real_api 2/LOONGARCH_ADAPTATION.md` | 国产化 / 龙芯部署注意点 |
| `A1proj_real_api 2/data/README.md` | 手册目录用法 |
| `A1proj_real_api 2/frontend/README.md` | Vite + Vue 模板说明（脚手架默认文案） |

---

## 9. 阅读建议

1. 先看根目录五份 PDF，对齐需求 / 设计 / 测试 / 部署口径。  
2. 再看 `ARCHITECTURE.md` 和本文件第 3、4 节，定位代码模块。  
3. 对话与检索从 `chat.py`、`rag_chain.py`、`cnc_agent.py` 读起。  
4. 知识入库从 `sync_service.py` 与 `pipeline/` 读起。  
5. 专利与答辩材料分别对应 `PATENT_CORE_CONTENT.md`、`DEFENSE_DRAFT.md`。
