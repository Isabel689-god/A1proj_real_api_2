# 维修手册数据目录

将 **PDF / DOCX** 维修手册放在此目录。系统会：

1. 启动时自动检测文件变更并同步到知识库
2. 通过 `POST /knowledge/sync` 手动触发全量同步
3. 使用真实 Embedding API 构建 FAISS 向量索引

支持实时增删改文件后重新同步。
