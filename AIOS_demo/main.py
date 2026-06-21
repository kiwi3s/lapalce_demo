import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import chromadb
import json
import os
from chromadb.config import Settings
from config import settings
import database
from models import KnowledgeAssetCreate, KnowledgeAsset, SearchResult, AskRequest, AskResponse

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

database.init_db()

from embedding_service import get_embedding
from rerank_service import rerank
from llm_service import ask_llm
from chroma_store import collection

app = FastAPI(title="知识资产问答工作台")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def init_data():
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM knowledge_assets")
    if cursor.fetchone()[0] == 0:
        samples = [
            {"title": "AIOS平台介绍", "content": "AIOS是一个面向企业的智能体操作平台，支持知识库、工具调用、工作流编排和多智能体协作。", "tags": ["AIOS", "平台", "智能体"]},
            {"title": "数字资产知识库", "content": "数字资产知识库用于沉淀企业文档、业务流程、销售资料、客户案例和产品说明，并支持智能检索和问答。", "tags": ["知识库", "数字资产", "检索"]},
            {"title": "Agent工作流", "content": "Agent可以通过任务拆解、工具调用、上下文记忆和结果校验完成复杂任务，但需要可观测性和权限控制来保证可靠性。", "tags": ["Agent", "工作流", "智能体"]}
        ]
        for s in samples:
            cursor.execute("INSERT INTO knowledge_assets (title, content, tags) VALUES (?, ?, ?)",
                          (s["title"], s["content"], json.dumps(s["tags"], ensure_ascii=False)))
            asset_id = cursor.lastrowid
            embedding = get_embedding(s["content"])
            collection.add(
                ids=[str(asset_id)],
                embeddings=[embedding],
                metadatas=[{"title": s["title"], "tags": json.dumps(s["tags"])}],
                documents=[s["content"]]
            )
        conn.commit()

init_data()

@app.get("/api/assets")
def get_assets():
    logger.info("GET /api/assets - 获取知识资产列表")
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, content, tags, created_at FROM knowledge_assets ORDER BY created_at DESC")
    rows = cursor.fetchall()
    result = [{"id": r["id"], "title": r["title"], "content": r["content"], "tags": json.loads(r["tags"]), "created_at": r["created_at"]} for r in rows]
    logger.info(f"返回 {len(result)} 条资产")
    return result

@app.post("/api/assets")
def create_asset(asset: KnowledgeAssetCreate):
    logger.info(f"POST /api/assets - 新增资产: {asset.title}")
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO knowledge_assets (title, content, tags) VALUES (?, ?, ?)",
                  (asset.title, asset.content, json.dumps(asset.tags, ensure_ascii=False)))
    asset_id = cursor.lastrowid
    conn.commit()
    embedding = get_embedding(asset.content)
    collection.add(
        ids=[str(asset_id)],
        embeddings=[embedding],
        metadatas=[{"title": asset.title, "tags": json.dumps(asset.tags)}],
        documents=[asset.content]
    )
    logger.info(f"资产创建成功, id={asset_id}, 已写入向量库")
    return {"id": asset_id, "title": asset.title, "content": asset.content, "tags": asset.tags}

@app.delete("/api/assets/{asset_id}")
def delete_asset(asset_id: int):
    logger.info(f"DELETE /api/assets/{asset_id} - 删除资产")
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM knowledge_assets WHERE id = ?", (asset_id,))
    conn.commit()
    collection.delete(ids=[str(asset_id)])
    logger.info(f"资产删除成功, id={asset_id}, 已从向量库移除")
    return {"ok": True}

@app.get("/api/search")
def search_assets(q: str, top_n: int = 3):
    logger.info(f"GET /api/search - 查询: {q}, top_n={top_n}")
    query_embedding = get_embedding(q)
    results = collection.query(query_embeddings=[query_embedding], n_results=min(10, collection.count()))
    if not results["ids"][0]:
        logger.warning(f"查询 [{q}] 未命中任何结果")
        return []
    docs = results["documents"][0]
    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    conn = database.get_db()
    cursor = conn.cursor()
    candidates = []
    for i, doc in enumerate(docs):
        aid = int(ids[i])
        cursor.execute("SELECT id, title, content, tags FROM knowledge_assets WHERE id = ?", (aid,))
        row = cursor.fetchone()
        if row:
            candidates.append({
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "tags": json.loads(row["tags"]),
                "doc": doc
            })
    reranked = rerank(q, [c["doc"] for c in candidates], top_n=top_n)
    final = []
    for c in candidates:
        if c["doc"] in reranked:
            final.append({"id": c["id"], "title": c["title"], "content": c["content"], "tags": c["tags"], "score": 0.9})
    logger.info(f"检索完成, 候选{len(candidates)}条, 重排序后返回{len(final[:top_n])}条")
    return final[:top_n]

@app.post("/api/ask", response_model=AskResponse)
def ask_question(req: AskRequest):
    query = req.query
    logger.info(f"POST /api/ask - 问题: {query}")
    results = search_assets(query, top_n=10)
    reranked_results = rerank(query, [r["content"] for r in results], top_n=3)
    sources = []
    context_parts = []
    for r in results:
        if r["content"] in reranked_results:
            sources.append({"id": r["id"], "title": r["title"], "content": r["content"]})
            context_parts.append(r["content"])
    context = "\n\n".join(context_parts)
    logger.info(f"检索到 {len(sources)} 条上下文, 准备调用LLM...")
    logger.info(f"=== 构建的 Prompt ===\n[System] 你是知识库助手，只根据以下知识回答，不要编造。\n知识：{context}\n[User] {query}\n=======================")
    answer, model_used = ask_llm(query, context)
    trace = {
        "query": query,
        "retrieved_assets": [{"id": s["id"], "title": s["title"]} for s in sources],
        "model_used": model_used,
        "final_answer": answer
    }
    logger.info(f"问答完成, 使用模型: {model_used}")
    return {"answer": answer, "sources": sources, "trace": trace}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

