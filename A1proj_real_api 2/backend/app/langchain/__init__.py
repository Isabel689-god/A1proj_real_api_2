"""
LangChain integration module.

- ``rag_chain.py`` — LCEL RAG chain with vision + keyword + vector + graph retrieval.
- ``vector_store.py`` — DashVector vector store wrapper.
- ``dashscope_embeddings.py`` — DashScope OpenAI-compatible embeddings (bypasses tiktoken).
"""
from app.langchain.rag_chain import RAGChain, rag_chain
from app.langchain.vector_store import DashVectorStore
