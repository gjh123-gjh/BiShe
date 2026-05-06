# 大连红色旅游知识图谱构建 - 脚本说明文档 (README)

本项目包含了一套完整的从互联网非结构化文本中构建红色旅游知识图谱的工具链。脚本存放在 `d:\BiShe\scripts` 目录下。

## 1. 系统开发环境
- **语言**: Python 3.x
- **依赖库**: 
  - `requests`: 网络请求
  - `lxml`: 高效 HTML 解析
  - `re`: 正则表达式匹配
  - `json/csv`: 数据交换与存储
  - `pandas`: (可选) 数据验证

## 2. 脚本流水线 (Pipeline)
为了获得最终的知识图谱数据，请按照以下顺序执行脚本：

### 第一步：数据采集 (Data Collection)
- **脚本**: `spider_red_tourism.py`
- **功能**: 从大连本地宝和腾讯新闻（大观新闻）爬取红色旅游文章。
- **输出**: `red_tourism_data.csv` (原始数据)

### 第二步：数据预处理 (Data Preprocessing)
- **脚本**: `data_preprocessing.py`
- **功能**: 去除网页噪声（广告、提示语）、清洗格式、基于指纹特征进行内容去重。
- **输出**: `red_tourism_cleaned.csv` (纯净语料)

### 第三步：知识抽取 (Knowledge Extraction - NER)
- **脚本**: `entity_extraction.py`
- **功能**: 识别文中的命名实体。类别包括：红色人物、红色场馆、历史事件。
- **输出**: `extracted_entities.csv` (初始实体集)

### 第四步：知识对齐 (Knowledge Alignment)
- **脚本**: `knowledge_alignment.py`
- **功能**: 实体归一化。处理子串重叠、合并同义项、剔除残留噪声词。
- **输出**: `aligned_entities.csv` (知识图谱节点表)

### 第五步：三元组关系抽取 (Relationship Extraction)
- **脚本**: `relationship_extraction.py`
- **功能**: 通过上下文共现分析和谓词匹配，自动发现实体间的语义关联（如：战友、位于、纪念等）。
- **输出**: `relationships.csv` (知识图谱边/关系表)

## 3. 产出物说明
- **`aligned_entities.csv`**: 包含所有清洗后的实体节点及其出现权重。可直接映射为 Neo4j 中的 **Nodes**。
- **`relationships.csv`**: 包含 (Subject-Relation-Object) 三元组。可直接映射为 Neo4j 中的 **Edges**。

## 4. 辅助工具
- **`research_fetch.py`**: 开发阶段用于嗅探网页结构和调试解析规则的辅助脚本。

---

**备注**: 本脚本集专为大连红色旅游领域定制，采用了基于领域的正则表达式与启发式算法，具有较高的抽取准确率。
