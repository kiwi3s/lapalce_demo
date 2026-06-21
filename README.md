## 回答

### 1. 你如何设计知识资产的数据结构？

采用  双库存储 设计：结构化元数据存 SQLite，向量数据存 ChromaDB，通过自增 ID 双写关联。

SQLite 表结构 (`knowledge_assets`)：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK AUTOINCREMENT | 主键，同时也是 ChromaDB 的向量 ID |
| `title` | TEXT NOT NULL | 资产标题 |
| `content` | TEXT NOT NULL | 资产正文内容（用于向量化） |
| `tags` | TEXT | JSON 数组字符串，如 `["AIOS","平台"]` |
| `created_at` | TIMESTAMP DEFAULT NOW | 创建时间 |

ChromaDB 集合 (`knowledge_assets`)：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | str(asset_id) | 与 SQLite ID 对应 |
| `embedding` | float[1024] | BGE-M3 生成的向量 |
| `document` | str | 原始 content 文本 |
| `metadata` | {title, tags} | 附加元信息，支持按条件过滤 |

- SQLite 负责 CRUD 展示、标签管理、时间排序等结构化查询
- ChromaDB 负责语义相似度检索
- 新增时双写、删除时双删，通过 asset_id 保持一致性
- 标签用 JSON 字符串存储而非关联表，因为本项目场景下标签数量少且无需复杂联查

---

### 2. 你如何实现检索？

采用 BGE-M3 召回 + BGE-reranker 精排 的两阶段检索策略：

#### 阶段一：粗召回（ChromaDB）

```
用户查询 → BGE-M3 向量化 → 1024维 query_vector
         → ChromaDB cosine_similarity(query_vector, all_embeddings)
         → 返回 Top10 候选文档（含 id, document, metadata）
```

#### 阶段二：精排重排（BGE-reranker）

```python
# rerank_service.py 核心逻辑
from sentence_transformers import CrossEncoder
reranker = CrossEncoder(reranker_path)

pairs = [(query, candidate_doc) for doc in candidates]
scores = reranker.predict(pairs)   # 输出 [0,1] 相关性得分
top3 = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:3]
```

从 Top10 缩减到 Top3，减少注入 LLM Prompt 的上下文长度，提升回答质量并降低 Token 成本

#### 完整检索链路

```
POST /api/ask { "query": "什么是AIOS？" }
  │
  ├─ search_assets(query, top_n=10)
  │    ├─ get_embedding(query)           # BGE-M3 向量化
  │    ├─ collection.query(n_results=10)  # ChromaDB 粗召回
  │    ├─ SQLite 补全 title/tags          # 关联查询
  │    └─ rerank(query, docs, top_n=3)    # Reranker 精排 Top3
  │
  └─ 取 Top3 结果的 context_parts → 拼 Prompt → LLM 生成回答
```

---

### 3. 如果要接入真实向量数据库，你会怎么改？

#### 方案A：Milvus

- 支持集群
- 使用IVF_FLAT 基于 聚簇与倒排索引，显著降低搜索的时间复杂度
- 支持标量过滤，方便实现多租户模式

#### 方案B：Elasticsearch

- 支持分片
- 可用性高
- 支持混合检索（BM25 关键词 + 向量语义融合）

#### 方案C：第三方服务

如阿里云等

- 开箱即用
- 快速交付

---

### 4. 如果要支持多租户，你会怎么改？

1.引入 JWT 标识各租户，做鉴权

2.数据库可以使用 PostgreSQL 基于schema分库，实现数据隔离

3.做限流限额，每个租户各自独立上限（API限流，模型调用限额）

可以基于Redis，做计数器；基于租户id+用户id做滑动窗口限流



### 5. 如果这个系统上线到真实 ToB 场景，你最担心的问题是什么？

按优先级排列：

1.幻觉
不可避免的,大模型仍可能生成看似合理但知识库中不存在的信息。一次错误回答可能导致严重后果。

- 可通过冗余提示词加强约束；
- 明确引用，阈值过低，明确拒绝回答；
- 通过nlp后处理识别知识库未覆盖语义；
- 收集人工反馈，优化提示词与知识库；

2.并发性能问题

向量化模型大量占用服务器资源，或推理延迟

- 向量化操作需异步处理，写入消息队列
- 加入向量缓存与llm缓存提效降本
- 大量上下文消耗过量token

3.知识库过时

企业文档可能过时、矛盾或格式混乱

- 做一致性检查，
- 定期清洗




## 启动准备

请确保您的电脑安装了node,python==3.11.9,ollama（备选）

推荐使用conda配置虚拟环境

如您欲配置api key 可在`prod\AIOS_demo\.env`中配置您的百炼sk,

请在 AIOS_demom目录下 运行 `pip install -r requirements.txt` 



注意 本项目使用到`BGE-M3`与`BGE-reranker-large` 请下载并放在`prod\AIOS_demo\models`

如下载遇到问题，可以使用以下链接下载

```
链接: https://pan.baidu.com/s/1aBnccvCraPP0vlfDYzjLFg?pwd=8hmx 提取码: 8hmx
```



`prod\AIOS_demo\start.bat ` 用来启动后端服务，也可在 AIOS_demom目录下使用  `python main.py`

`prod\frontend\start.bat`用来启动前端服务

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Vue3 + Vite + Element Plus + Axios | 单页面应用，资产 CRUD + 智能问答 |
| **后端** | FastAPI + Uvicorn | RESTful API |
| **结构化存储** | SQLite | 知识资产元数据（标题、内容、标签） |
| **向量存储** | ChromaDB | 文档向量化存储与相似度检索 |
| **向量化** | BGE-M3 | 多语言嵌入模型，1024 维向量 |
| **重排序** | BGE-reranker-large | CrossEncoder 精排，提升检索精度 |
| **大模型** | Qwen-max API / Ollama | 双路调用：优先云端 API，失败降级本地模型 |

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端界面 |
| http://localhost:8000/docs | 后端 API 文档（Swagger UI） |

---

## 功能说明

### 知识资产管理

- **列表展示**: 表格展示所有知识资产（ID、标题、内容摘要、标签、创建时间）
- **新增资产**: 填写标题、内容、标签（逗号分隔），同步写入 SQLite + ChromaDB
- **删除资产**: 确认删除，双向清除（SQLite + 向量库）

### 智能问答（RAG Agent）

完整链路：

```
用户提问
  → 查询词向量化 (BGE-M3)
  → ChromaDB 相似度召回 (候选 Top10)
  → BGE-reranker 精排重排序 (返回 Top3)
  → 构建 Prompt（系统指令 + 检索上下文 + 用户问题）
  → LLM 生成回答 (Qwen API 优先, 失败降级 Ollama)
  → 返回 { answer, sources[], trace{} }
```

- **answer**: 大模型生成的自然语言回答
- **sources**: 引用的知识资产来源列表
- **trace**: Agent 链路追踪 JSON（query → retrieved_assets → model_used → final_answer）

###### 时间匆忙，言至于此，如有疏漏不解，请联系 zhenlin0s@outlook.com