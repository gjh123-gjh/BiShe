# 大连红色旅游知识图谱系统

本项目旨在搭建一个面向**大连红色旅游**场景的知识图谱与智能问答系统。通过预处理红色旅游相关数据，构建图谱并提供可视化与在线问答服务，方便用户了解红色场馆、人物、展品、历史事件、旅游服务等信息。

---

## 核心功能

- **知识图谱构建**：从 CSV / JSON 数据抽取三元组，清洗、去重并导入 Neo4j。
- **图谱可视化**：基于 D3.js 与 ECharts 展示实体和关系网络。
- **AI 问答**：结合 DeepSeek 向量检索和预训练模型，实现自然语言问答。
- **REST API**：Flask 提供图谱数据查询、问答接口。
- **前端展示**：Vue3 + Element Plus 实现交互式仪表盘、问答页面和实体详情。

---

## 技术栈与理论

| 层级 | 技术 | 说明 |
|------|------|------|
| 数据存储 | [Neo4j](https://neo4j.com) | 图数据库，适合存储实体-关系网络。 |
| 后端 | Python 3.10+，Flask | 提供 API 和图谱构建脚本。 |
| AI 服务 | DeepSeek 向量检索 | 将文本嵌入，配合预训练模型进行问答。 |
| 前端 | Vue3、Element Plus、D3.js、ECharts | 构建SPA，呈现图谱和问答界面。 |
| 数据处理 | pandas、networkx 等 | 对 CSV/JSON 数据做预处理、去重与三元组生成。 |
| 部署工具 | requirements.txt、package.json | 管理 Python/Node 依赖。 |

### 知识图谱简介

知识图谱由 **节点（实体）** 和 **关系（边）** 组成，本项目的实体类别包括：
- 红色场馆
- 红色人物
- 红色展品
- 历史事件
- 旅游服务

三元组（`subject`‑`predicate`‑`object`）数据来自 `大连红色旅游_节点.csv`、`大连红色旅游_关系.csv` 等，经 `build_kg.py` 预处理后生成 JSON 并导入 Neo4j。`export_kg.py` 可用于从数据库导出。

### AI 问答原理

问答流程见 `qa_pipeline.py`：
1. 用户输入转向量（`embed_and_index.py` 建立索引）。
2. 使用 DeepSeek 向量检索找到相关文本段落。
3. 通过大模型生成回答（`deepseek_client.py` 为封装的 API 客户端）。
4. 支持离线演示（`qa_demo_offline.py`、`qa_complete_demo.py`）。

---

## 目录结构

### 后端核心组件

**数据处理层**
- `大连红色旅游三元组_预处理.json`：预处理后的三元组数据源（主输入）
- `preprocessing.py`：原始数据预处理脚本，负责数据清洗、标准化并导出JSON格式
- `node.py`：从预处理JSON生成实体/关系CSV文件
- `dedupe_and_sentence.py`：数据去重与合并工具，支持自然语言句子生成
- `strong_merge.py`：高级节点合并工具（APOC优先策略）

**知识图谱层**
- `build_kg.py`：将预处理数据导入Neo4j，创建节点、标签和关系
- `Neo4j_red.py`：Neo4j数据库连接封装模块
- `Neo4j_reset.py`：数据库重置工具
- `export_kg.py`：知识图谱数据导出工具

**AI问答层**
- `qa_pipeline.py`：智能问答核心流程，集成DeepSeek检索器
- `deepseek_client.py`：DeepSeek API客户端封装
- `embed_and_index.py`：文本嵌入和索引构建
- `qa_demo_offline.py`、`qa_complete_demo.py`：问答演示脚本

**Web服务层**
- `app.py`：Flask后端API服务，提供RESTful接口
- `API.py`：额外的API接口定义

### 前端组件 (red-tourism-vue)

**核心页面**
- `Dashboard.vue`：主控制面板，整合问答、图谱和详情展示

**可视化组件**
- `KnowledgeGraph.vue`：基于D3.js的知识图谱可视化
- `QAChat.vue`：智能问答交互界面
- `EntityDetail.vue`：实体详细信息展示
- `NodeCard.vue`、`RelationList.vue`：基础UI组件

**服务层**
- `api.js`：前后端API通信封装
- `graphData.js`：图谱数据处理工具
- `store/index.js`：Vue状态管理

### 配置与工具文件

- `package.json`：Node.js依赖配置
- `.env`：环境变量配置文件
- `requirements.txt`：Python依赖列表
- `vue.config.js`：Vue CLI配置



## 功能特性

### 🔧 数据处理
- 自动化数据清洗和标准化
- 智能去重和实体合并
- 多格式数据导出（JSON/CSV）

### 📊 知识图谱
- Neo4j图数据库存储
- 实体关系可视化展示
- 支持多标签分类管理

### 🤖 智能问答
- 基于检索增强生成（RAG）的问答系统
- DeepSeek大模型集成
- 自然语言理解与回答

### 🖥️ 可视化界面
- 响应式Web前端设计
- 交互式图谱探索
- 实时问答对话

## 快速开始

### 环境准备

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装前端依赖
cd red-tourism-vue
npm install



# 1. 启动后端API服务
python app.py

# 2. 启动前端开发服务器
cd red-tourism-vue
npm run serve



# 1. 预处理原始数据
python preprocessing.py

# 2. 构建知识图谱
python build_kg.py

# 3. 验证数据导入
python export_kg.py
```