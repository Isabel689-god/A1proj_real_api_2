# A1proj CNC 故障诊断系统 — 架构文档

> 版本：2026-08-09 | 总代码量 ≈16,300 行（不含JSON数据）

---

## 一、系统概览

```
┌─────────────────────────────────────────────────────────────┐
│  浏览器                                                     │
│  ┌──────────────────────┬──────────────────┬──────────────┐ │
│  │ ChatSidebar          │ ChatMessageList  │ RightPanel   │ │
│  │ 会话列表              │ 消息流(SSE)       │ SOP + 报告    │ │
│  └──────────────────────┴──────────────────┴──────────────┘ │
│  前端: Vue 3 + Pinia + Element Plus + TypeScript            │
├─────────────────────────────────────────────────────────────┤
│  FastAPI :8000                                              │
│  ┌──────────┬──────────┬──────────┬──────────┬───────────┐ │
│  │ /chat    │ /agent   │ /knowledge│ /user   │ /monitor  │ │
│  │ RAG直出  │ LangGraph│ 同步/图谱 │ 登录/权限│ 系统状态   │ │
│  └──────────┴──────────┴──────────┴──────────┴───────────┘ │
│  后端: FastAPI + LangChain + SQLAlchemy + MySQL             │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、后端架构

### 2.1 目录结构

```
backend/app/
├── main.py                 # FastAPI 入口，挂载路由
├── api/v1/
│   ├── chat.py             # 对话核心（RAG + Agent 双路径）
│   ├── knowledge.py        # 知识库管理（上传/同步/图谱）
│   ├── user.py             # 登录/权限/用户管理
│   ├── maintenance.py      # 维修记录 CRUD + CSV 导出
│   └── monitor.py          # 系统运维监控面板
├── agent/
│   └── cnc_agent.py        # LangGraph Agent（4工具 + SOP闭环）
├── langchain/
│   ├── rag_chain.py        # RAG 检索链（向量+关键词+图谱三路融合）
│   ├── vector_store.py     # DashVector 云向量库
│   └── local_vector_store.py  # FAISS 本地向量库（兜底）
├── knowledge/
│   ├── sync_service.py     # 全量同步引擎
│   ├── graph_builder.py    # JSON 图谱构建（设备-部件-故障-文档）
│   ├── graph_service.py    # 图谱查询（故障定位/文档扩展）
│   └── dynamic_store.py    # 动态知识存储（案例+修正）
├── pipeline/
│   ├── extractor.py        # 三元组抽取（LLM批量）
│   ├── validator.py        # 三元组校验
│   ├── deduper.py          # 消重
│   └── db_writer.py        # MySQL 入库
├── services/
│   ├── sop_service.py      # SOP 版本管理（MySQL 持久化）
│   ├── session_service.py  # 会话 CRUD（MySQL）
│   ├── user_service.py     # 用户/权限
│   └── group_service.py    # 权限组
├── db/
│   ├── models.py           # SQLAlchemy ORM 模型
│   └── engine.py           # 数据库引擎
└── core/
    ├── auth.py             # JWT 鉴权
    └── config.py           # 全局配置
```

### 2.2 对话引擎（双路径）

| 路径 | 端点 | 机制 | 适用场景 |
|---|---|---|---|
| RAG 直出 | `POST /chat` | 检索→模板填充→流式输出 | 标准故障诊断 |
| Agent | `POST /chat/agent` | LangGraph 多工具自主规划 | 复杂排障 |

**Agent 四工具：**

```
1. search_case_library    → 案例优先检索（置信度>=0.70 直接复用）
2. search_knowledge_base  → 检索维修手册（DashVector/FIASS + 关键词）
3. search_mysql_graph     → 查询 MySQL 知识图谱（故障→原因→方案链路）
4. sop_manage             → SOP 状态管理（闭包捕获 session_id）
```

### 2.3 SOP 管理

- **首轮冻结**：`save_version()` 硬守卫——已有非空步骤绝不覆盖
- **状态流转**：Agent 从回复文本中自动解析步骤完成意图，批量更新
- **存储**：MySQL `sys_sop_version` 表，按 `session_id` 隔离
- **锁定**：首版 SOP 内容不变，只更新 `step_status` 和 `step_note`

### 2.4 知识同步引擎

```
PDF/DOCX 手册文件
      │
      ▼
  parse_manual_file()          # 文档解析
      │
      ▼
  KnowledgeSyncService.sync()
      │
      ├─► knowledge.json       # 全量文档
      ├─► graph.json           # JSON 图谱（节点+边）
      ├─► DashVector/FAISS     # 向量索引
      ├─► TripleExtractor      # 三元组抽取→MySQL 图谱
      └─► reload()             # 刷新对话缓存
```

### 2.5 鉴权

- **JWT**：`python-jose` + HS256，用户 24h / 管理员 12h
- **兼容**：管理员接口同时支持 `Authorization: Bearer <jwt>` 和 `X-Admin-Token`
- **依赖注入**：`verify_admin` → 优先 JWT → 回退 X-Admin-Token

---

## 三、前端架构

### 3.1 目录结构

```
frontend/src/
├── views/
│   ├── LoginView.vue         # 登录页（JWT 流程）
│   ├── ChatView.vue          # 主聊天界面
│   └── AdminView.vue         # 管理端（7个子面板）
├── components/
│   ├── ChatSidebar.vue       # 左侧会话列表 + 新建任务
│   ├── ChatMessageList.vue   # 消息流渲染（含工具调用卡片）
│   ├── ChatComposer.vue      # 底部输入框（多模态）
│   ├── RightPanel.vue        # 右侧面板容器
│   ├── SopFlow.vue           # SOP 步骤流程图
│   ├── RepairReport.vue      # 维修报告提交
│   └── KnowledgeGraph.vue    # MySQL 图谱可视化
├── stores/
│   └── chat.ts               # Pinia 全局状态
├── api/
│   └── chat.ts               # SSE 流式通信
├── utils/
│   └── auth.ts               # JWT token 管理 + authFetch
└── assets/styles/
    └── global.css            # 全局主题（深色/浅色 + Element Plus 覆盖）
```

### 3.2 页面结构

**ChatView（主聊天界面）：**
```
┌──────────┬─────────────────────┬──────────┐
│ Sidebar  │ ChatMainArea        │ RightPanel│
│          │ ┌─────────────────┐ │          │
│ 会话列表  │ │ ChatMessageList │ │ SOP流程  │
│ 新建任务  │ │ (SSE流式消息)    │ │ ──────── │
│          │ ├─────────────────┤ │ 闭环报告  │
│          │ │ ChatComposer    │ │          │
│          │ │ (输入框)         │ │          │
│          │ └─────────────────┘ │          │
└──────────┴─────────────────────┴──────────┘
```

**AdminView（管理端 7 面板）：**
```
┌────────────────────────────────────────────┐
│ 左侧菜单                                    │
│  ├─ 组织架构与权限管控                        │
│  ├─ 手册文件在线管理（三线表）                 │
│  ├─ 维修案例库（三线表）                      │
│  ├─ 全局检修记录（三线表）                    │
│  ├─ 维修记录与总结                            │
│  ├─ 知识图谱(MySQL)                          │
│  └─ 系统运维监控                             │
└────────────────────────────────────────────┘
```

### 3.3 状态管理（Pinia）

| 状态 | 类型 | 说明 |
|---|---|---|
| `sessions` | ConversationSession[] | 会话列表 |
| `activeSessionId` | string | 当前活跃会话 |
| `lockedSOP` | object \| null | 首轮冻结的 SOP 结构 |
| `sopTick` | number | SOP 变更计数器（强制刷新） |
| `globalReports` | array | 提报记录（localStorage） |
| `isLoggedIn` / `username` / `group` / `permissions` | — | 鉴权状态 |

**关键 computed：**
- `messages` → `activeSession.messages`
- `reportLocked` → `globalReports` 中是否有当前会话的提报记录

### 3.4 数据流

```
用户输入 → sendMessage()
           │
           ├─ push userMsg to session.messages
           ├─ sendChatMessageStream() → SSE fetch
           │     │
           │     ├─ 'text' → append to assistantMsg.content
           │     ├─ 'sop_version' → lockedSOP (首轮) + sopTick++
           │     ├─ 'sop_state' → 更新步骤状态
           │     ├─ 'tool_start/end' → tool_calls[]
           │     └─ 'done' → status = 'done'
           │
           └─ loading = false
```

---

## 四、数据模型（MySQL 核心表）

| 表 | 用途 |
|---|---|
| `users` | 用户（username/password/group/is_online） |
| `sessions` | 会话（session_id/user_id/message_count） |
| `messages` | 消息（session_id/role/content） |
| `sys_sop_version` | SOP 版本（session_id/steps/issue_fingerprint） |
| `sys_maintenance_record` | 维修记录（fault_type/cause/solution/synced） |
| `fault` / `fault_cause` / `solution` / `relation` | MySQL 知识图谱 |
| `permission_groups` | 权限组配置 |

---

## 五、主题系统

- **深色模式**：`#0a0f19` 底色 + `#00b4a0` 青绿主色
- **浅色模式**：`#f0f2f5` 底色 + `#009688` 主色
- **CSS 变量**：`--primary-color`、`--bg-card`、`--border-glass` 等全局驱动
- **去 AI 味**：已移除玻璃拟态/霓虹光效/雷达动画，改为干净边框工业风
- **三线表**：维修记录/案例库/手册管理统一使用经典三线表样式

---

## 六、部署

```bash
# 后端
cd backend
PYTHONPATH="./backend:$PYTHONPATH" uv run uvicorn app.main:app --port 8000

# 前端
cd frontend
npx vite --port 5173
```

- 后端端口：8000
- 前端端口：5173
- MySQL：RDS `rm-2ze87w46ypv5f1173ko` / 数据库 `ruanjiandata`
