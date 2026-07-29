# 龙芯环境适配说明

本项目的知识图谱前端已经改为 Vue + ECharts 本地依赖渲染，不再通过 iframe 加载后端静态 HTML，也不再依赖 CDN 版 ECharts。这样在龙芯 Linux 环境中只需要安装对应架构的 Node.js、Python 和系统库即可运行。

## 推荐运行环境

- 操作系统：LoongArch64 Linux 发行版，例如 Loongnix、统信 UOS、麒麟等。
- Node.js：建议 20 LTS 或 22 LTS 的 loong64/loongarch64 原生包。
- Python：3.11 或以上。
- 数据库：MySQL 或 MariaDB 的 LoongArch64 原生包。
- OCR/PDF 可选系统依赖：`tesseract-ocr`、`poppler-utils`，用于图片 OCR 与 PDF 渲染解析。

## 前端启动

```bash
cd frontend
npm install
npm run dev:loongarch
```

默认访问：

```text
http://127.0.0.1:5173
```

如果需要让同一局域网设备访问，使用龙芯机器的局域网 IP：

```text
http://<龙芯机器IP>:5173
```

## 后端启动

```bash
cp .env.example .env
uv sync
uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

如果龙芯环境暂时没有 `uv` 可用，可以使用系统 Python：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

## 图谱前端接口

新版 `frontend/src/components/KnowledgeGraph.vue` 直接调用：

- `GET /knowledge/graph`
- `GET /knowledge/graph?entity_type=device`
- `GET /knowledge/graph/node/{biz_id}`

Vite 开发环境已通过 `frontend/vite.config.ts` 将 `/knowledge` 代理到 `127.0.0.1:8000`。生产部署时可以通过 `VITE_API_BASE` 指向后端地址。

## 龙芯注意事项

- 不使用固定 x86 Docker 镜像作为默认启动方式，优先使用龙芯系统包和本机编译/安装依赖。
- 前端依赖均为 JS/TS 生态常规包，ECharts 在浏览器端 Canvas 渲染，不需要 x86 原生二进制。
- 后端若安装含编译扩展的 Python 包，应使用龙芯发行版提供的编译工具链和 Python 头文件。
- `.env` 中的外部模型 API Key、MySQL 连接信息、DashVector 配置需要在目标机器上重新填写。
