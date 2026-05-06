# 大连红色旅游知识图谱与智能问答系统

本项目旨在构建一个针对**大连红色旅游**资源的知识图谱，并结合大语言模型（DeepSeek）实现智能问答（RAG）。

---

## 📂 项目目录结构与文件功能清单

### 1. 核心业务流水线 (根目录)

| 文件名 | 类型 | 功能描述 |
| :--- | :--- | :--- |
| `app.py` | 后端 | **核心服务**：基于 Flask 的 API 后端，提供图谱数据获取与 AI 问答接口。 |
| `build_kg.py` | 构建 | **核心导入**：将预处理后的 JSON 数据批量导入 Neo4j 数据库。 |
| `qa_pipeline.py` | AI | **核心问答**：问答系统的 RAG 流水线，负责检索向量库并调用 AI 生成回答。 |
| `preprocessing.py` | 预处理 | **数据转化**：将手工抽取的 `.txt` 三元组文件转化为 `大连红色旅游三元组_预处理.json`。 |
| `.env` | 配置 | **环境变量**：存放 API Key（OpenAI/DeepSeek）及数据库密码。 |

### 2. 数据库与知识图谱工具 (根目录)

| 文件名 | 类型 | 功能描述 |
| :--- | :--- | :--- |
| `Neo4j_red.py` | 工具 | Neo4j 数据库驱动的封装模块，供其他脚本调用。 |
| `Neo4j_reset.py` | 工具 | **数据库重置**：一键清空数据库中的所有节点与关系（请谨慎使用）。 |
| `export_kg.py` | 工具 | 将图数据库中的数据导出为本地备份。 |
| `strong_merge.py` | 优化 | **高级合并**：使用 Neo4j APOC 插件或手动逻辑合并名称相近的重复节点。 |
| `dedupe_and_sentence.py`| 优化 | **去重与语效**：实体去重，并生成可用于训练或展示的自然语言描述句子。 |
| `node.py` | 产出 | 将处理好的 JSON 数据转换为用于外部导入的 `.csv` 节点与关系文件。 |

### 3. AI 服务与演示 (根目录)

| 文件名 | 类型 | 功能描述 |
| :--- | :--- | :--- |
| `deepseek_client.py` | API | DeepSeek 官方 API 的封装客户端。 |
| `embed_and_index.py` | 向量化 | 对旅游文本进行 Embedding 并建立 FAISS 索引，支持语义搜索。 |
| `qa_demo_offline.py` | 演示 | 离线版本的问答测试脚本，无需启动 Web 服务。 |
| `API.py` | 备份 | 项目早期的 API 定义，目前作为代码参考保留。 |

### 4. 辅助脚本目录 (`/scripts`)
该目录主要存放数据采集与早期的知识抽取逻辑。

| 文件名 | 功能描述 |
| :--- | :--- |
| `spider_red_tourism.py` | 基于 Python 的爬虫，用于抓取大连相关的红色旅游网页信息。 |
| `data_preprocessing.py` | 清洗爬虫抓取的原始 CSV 文本，去除广告、HTML 噪声等。 |
| `entity_extraction.py` | 从清洗后的文本中识别并抽取红色场馆、人物等实体。 |
| `relationship_extraction.py` | 从文本中识别实体间的关联关系（如：人物-出生地-地点）。 |
| `knowledge_alignment.py` | 知识对齐工具，消除不同来源、不同称呼下的同一实体冲突。 |

### 5. 前端展示项目 (`/red-tourism-vue`)
基于 Vue3 + Element Plus 的单页应用（SPA）。

- `src/components/KnowledgeGraph.vue`: 基于 D3.js 的力导向图可视化。
- `src/components/QAChat.vue`: 聊天对话界面组件。
- `src/views/Dashboard.vue`: 主仪表盘面板。

---



## 🚀 快速启动

1.  **数据就绪**：
    `python preprocessing.py` (生成 JSON) -> `python build_kg.py` (导入数据库)。
2.  **启动后端**：
    `python app.py` (默认端口 5000)。
3.  **启动前端**：
    `cd red-tourism-chat-ui && npm run dev`。
4.  **智能问答**：
    确保 `.env` 中有有效的 DeepSeek API Key。