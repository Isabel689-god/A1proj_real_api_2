# A1 后端：多模态检索 + 动态知识库（真实 API）

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 配置真实 API

复制 `.env.example` 为 `.env`，填写 OpenAI 兼容接口的 Key 与 Base URL（支持智谱、通义 DashScope 等）。

```env
ZHIPU_API_KEY=你的真实Key
ZHIPU_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
EMBEDDING_MODEL=text-embedding-v3
VISION_MODEL=qwen-vl-plus
ADMIN_TOKEN=请修改管理员Token
```

## 3. 放入维修手册

将 PDF / DOCX 放入项目根目录 **`data/`**（可随时增删，系统会检测变更）。

```bash
# 一键：同步手册 → 知识图谱 → 真实 Embedding 向量索引
PYTHONPATH=backend python scripts/sync_and_index.py
```

或分步：

```bash
PYTHONPATH=backend python scripts/build_maintenance_knowledge.py
PYTHONPATH=backend python scripts/build_vector_index.py
```

## 4. 启动服务

```bash
uvicorn app.main:app --app-dir backend --reload
```

访问 http://127.0.0.1:8000/docs

## 5. 功能接口说明

### 3. 多模态知识检索

| 接口 | 说明 |
|------|------|
| `POST /retrieve` | JSON：文本 + 图片URL + 设备型号 |
| `POST /retrieve/multipart` | 表单上传故障图片 + 文本 + 设备型号 |
| `POST /chat` | 问答（支持 `device_model`、`image_url`） |
| `POST /chat/stream/multipart` | 流式问答 + 上传图片 |

图片会先经 **真实视觉大模型** 分析，再与文本一起做语义检索与图谱故障定位。

### 4. 动态可迭代知识库 + 知识图谱

| 接口 | 说明 |
|------|------|
| `POST /knowledge/sync` | 从 `data/` 增量同步手册，重建图谱 |
| `POST /knowledge/cases` | 用户上传维修案例（待审核） |
| `POST /knowledge/cases/{id}/review` | 管理员审核（Header: `X-Admin-Token`） |
| `POST /knowledge/corrections` | 人工修正大模型回答入库 |
| `POST /knowledge/graph/query` | 图谱故障定位查询 |

审核通过的案例与修正条目会自动并入知识库；问答时会优先匹配人工修正经验。

## 6. 示例

**多模态检索：**

```json
POST /retrieve
{
  "query": "主轴报警 250",
  "device_model": "SINUMERIK 808D"
}
```

**上传案例：**

```bash
curl -X POST http://127.0.0.1:8000/knowledge/cases \
  -F "title=伺服过热处理" \
  -F "content=检查风扇与参数8300..." \
  -F "device_model=FANUC 0i"
```

**管理员审核通过：**

```bash
curl -X POST http://127.0.0.1:8000/knowledge/cases/case_xxx/review \
  -H "X-Admin-Token: 你的ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approve": true, "reviewer": "admin"}'
```
