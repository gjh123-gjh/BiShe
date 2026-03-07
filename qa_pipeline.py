"""
QA 流程：使用 DeepSeek 作为检索器，拼接证据并调用上游 LLM（由用户提供 LLM 调用函数）。
修改版本：适配重构后的知识图谱节点和关系（使用 kg_nodes.json 和 kg_rels.json）
"""
from typing import List, Dict, Callable, Any, Optional
from deepseek_client import DeepSeekClient
from pathlib import Path
import os
import json
import re

def load_env_file():
    """手动加载 .env 文件到环境变量"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())

load_env_file()

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# PROMPT_TEMPLATE = (
#     "你是一个大连红色旅游知识图谱专家问答系统。\n\n"
#     "【知识图谱数据结构】\n"
#     "你掌握的知识图谱包含以下类型数据：\n"
#     "1. 红色场馆：纪念馆、博物馆、遗址、陵园（有开放时间、地址、电话等属性）\n"
#     "2. 红色人物：革命人物、英雄模范（有出生时间、籍贯、事迹等属性）\n"
#     "3. 历史事件：重要革命事件（有时间、地点、参与者等属性）\n"
#     "4. 红色展品：文物、史料（有材质、特征、保存地点等属性）\n"
#     "5. 旅游服务：路线、交通、服务信息\n"
#     "6. 时间：历史时间节点\n"
#     "7. 地点：地理位置\n\n"
    
#     "【数据格式说明】\n"
#     "证据以三元组形式提供：\n"
#     "- 实体-关系-实体：(主体, 关系, 客体)\n"
#     "- 实体-属性-属性值：(主体, 属性, 属性值)\n\n"
    
#     "【回答要求】\n"
#     "1. 严格基于提供的证据回答，不添加图谱外信息\n"
#     "2. 识别证据中的实体关联，构建完整的知识网络\n"
#     "3. 按以下结构组织回答：\n"
#     "   📍 核心实体\n"
#     "   ├─ 基本信息\n"
#     "   ├─ 相关关系\n"
#     "   └─ 实用信息\n"
#     "4. 如果证据不足，明确说明\"知识图谱中相关信息不完整\"\n"
#     "5. 在末尾标注使用的证据ID\n\n"
    
#     "问题：{query}\n\n"
#     "知识图谱证据：\n{evidence}\n\n"
#     "请基于以上知识图谱证据回答问题："
# )
# 在 qa_pipeline.py 中修改 PROMPT_TEMPLATE

PROMPT_TEMPLATE = (
    "你是一个大连红色旅游知识图谱专家问答系统。\n\n"
    "【知识图谱数据结构】\n"
    "你掌握的知识图谱包含以下类型数据：\n"
    "1. 红色场馆：纪念馆、博物馆、遗址、陵园（有开放时间、地址、电话等属性）\n"
    "2. 红色人物：革命人物、英雄模范（有出生时间、籍贯、事迹等属性）\n"
    "3. 历史事件：重要革命事件（有时间、地点、参与者等属性）\n"
    "4. 红色展品：文物、史料（有材质、特征、保存地点等属性）\n"
    "5. 旅游服务：路线、交通、服务信息\n"
    "6. 时间：历史时间节点\n"
    "7. 地点：地理位置\n\n"
    
    "【数据格式说明】\n"
    "证据以三元组形式提供：\n"
    "- 实体-关系-实体：(主体, 关系, 客体)\n"
    "- 实体-属性-属性值：(主体, 属性, 属性值)\n\n"
    
    "【重要提示】\n"
    "1. **信息推理**：当证据中没有完全匹配的答案时，请根据已有信息进行合理推理。\n"
    "   例如：如果有“籍贯”信息，可以回答“出生地”；如果有“逝世时间”和“逝世地点”，可以回答“逝世地点”。\n"
    "2. **诚实回答**：如果确实没有相关信息，才回答“信息不完整”。\n"
    "3. **结构化输出**：按以下结构组织回答。\n\n"
    
    "【回答要求】\n"
    "1. 严格基于提供的证据回答，不添加图谱外信息\n"
    "2. 识别证据中的实体关联，构建完整的知识网络\n"
    "3. 按以下结构组织回答：\n"
    "   📍 核心实体\n"
    "   ├─ 基本信息\n"
    "   ├─ 相关关系\n"
    "   └─ 实用信息\n"
    "4. 在末尾标注使用的证据ID\n\n"
    
    "问题：{query}\n\n"
    "知识图谱证据：\n{evidence}\n\n"
    "请基于以上知识图谱证据回答问题："
)

class LocalKnowledgeGraphSearcher:
    """本地知识图谱搜索器，用于查询重构后的JSON文件数据"""
    
    def __init__(self, 
                 nodes_file_path: str = "kg_nodes.json", 
                 rels_file_path: str = "kg_rels.json"):
        """
        初始化知识图谱搜索器
        
        Args:
            nodes_file_path: 节点文件路径（默认 kg_nodes.json）
            rels_file_path: 关系文件路径（默认 kg_rels.json）
        """
        self.nodes_file_path = Path(nodes_file_path)
        self.rels_file_path = Path(rels_file_path)
        self.nodes = []
        self.rels = []
        self.node_id_map = {}  # id -> node 的映射，加速查找
        self.node_name_map = {}  # 名称 -> node 列表的映射，加速搜索
        
        # 加载节点数据
        self._load_nodes()
        
        # 加载关系数据
        self._load_relationships()
        
        # 构建节点关系索引
        self._build_relation_index()
    
    def _load_nodes(self):
        """加载节点数据"""
        if self.nodes_file_path.exists():
            try:
                with open(self.nodes_file_path, 'r', encoding='utf-8') as f:
                    self.nodes = json.load(f)
                
                # 构建ID映射
                for node in self.nodes:
                    node_id = node.get('id')
                    if node_id is not None:
                        self.node_id_map[node_id] = node
                    
                    # 构建名称映射（用于模糊搜索）- 适配重构后的数据结构
                    props = node.get('props', {})
                    node_name = props.get('名称') or props.get('实体名称', '')
                    if node_name:
                        if node_name not in self.node_name_map:
                            self.node_name_map[node_name] = []
                        self.node_name_map[node_name].append(node)
                
                print(f"✓ 成功加载 {len(self.nodes)} 个知识图谱节点")
                print(f"  - 节点类型分布：{self._get_node_type_stats()}")
            except Exception as e:
                print(f"✗ 加载节点文件失败: {e}")
        else:
            print(f"✗ 节点文件不存在: {self.nodes_file_path}")
            # 尝试查找其他可能的文件名
            self._try_alternative_files('nodes')
    
    def _load_relationships(self):
        """加载关系数据"""
        if self.rels_file_path.exists():
            try:
                with open(self.rels_file_path, 'r', encoding='utf-8') as f:
                    self.rels = json.load(f)
                print(f"✓ 成功加载 {len(self.rels)} 个知识图谱关系")
                print(f"  - 关系类型分布：{self._get_relation_type_stats()}")
            except Exception as e:
                print(f"✗ 加载关系文件失败: {e}")
        else:
            print(f"✗ 关系文件不存在: {self.rels_file_path}")
            # 尝试查找其他可能的文件名
            self._try_alternative_files('rels')
    
    def _try_alternative_files(self, file_type: str):
        """尝试查找其他可能的文件名"""
        alternatives = {
            'nodes': ['kg_nodes_clean.json', 'nodes.json', 'knowledge_graph_nodes.json'],
            'rels': ['kg_edges.json', 'kg_edges_clean.json', 'edges.json', 'relationships.json']
        }
        
        for alt_file in alternatives.get(file_type, []):
            alt_path = Path(alt_file)
            if alt_path.exists():
                print(f"  发现替代文件: {alt_file}")
                if file_type == 'nodes':
                    self.nodes_file_path = alt_path
                    self._load_nodes()
                else:
                    self.rels_file_path = alt_path
                    self._load_relationships()
                break
    
    def _get_node_type_stats(self) -> str:
        """获取节点类型统计"""
        type_count = {}
        for node in self.nodes:
            labels = node.get('labels', [])
            for label in labels:
                type_count[label] = type_count.get(label, 0) + 1
        
        stats = []
        for label, count in sorted(type_count.items(), key=lambda x: -x[1])[:5]:
            stats.append(f"{label}:{count}")
        return ", ".join(stats)
    
    def _get_relation_type_stats(self) -> str:
        """获取关系类型统计"""
        type_count = {}
        for rel in self.rels:
            rel_type = rel.get('type', '')
            type_count[rel_type] = type_count.get(rel_type, 0) + 1
        
        stats = []
        for rel_type, count in sorted(type_count.items(), key=lambda x: -x[1])[:5]:
            stats.append(f"{rel_type}:{count}")
        return ", ".join(stats)
    
    def _build_relation_index(self):
        """构建节点关系索引，用于快速查找相关实体"""
        self.node_relations = {}  # node_id -> list of relations
        
        for rel in self.rels:
            source = rel.get('source')
            target = rel.get('target')
            
            # 索引正向关系
            if source is not None:
                if source not in self.node_relations:
                    self.node_relations[source] = []
                self.node_relations[source].append({
                    'type': 'outgoing',
                    'relation': rel,
                    'target_id': target,
                    'target_node': self.node_id_map.get(target)
                })
            
            # 索引反向关系
            if target is not None:
                if target not in self.node_relations:
                    self.node_relations[target] = []
                self.node_relations[target].append({
                    'type': 'incoming',
                    'relation': rel,
                    'source_id': source,
                    'source_node': self.node_id_map.get(source)
                })
    
    def _get_node_name(self, node: Dict[str, Any]) -> str:
        """从节点中获取名称（适配两种数据格式）"""
        props = node.get('props', {})
        # 优先使用重构后的"名称"字段，如果没有则使用原来的"实体名称"
        return props.get('名称') or props.get('实体名称', f'未知实体_{node.get("id", "?")}')
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        根据查询内容搜索相关的节点和关系
        """
        # 提取查询中的关键词
        keywords = self._extract_keywords(query)
        
        # 识别问题类型
        question_type = self._identify_question_type(query)
        print(f"📝 问题类型识别: {question_type}")
        
        results = []
        matched_node_ids = set()
        
        # 策略1：精确匹配实体名称
        for node in self.nodes:
            node_name = self._get_node_name(node)
            if node_name and any(kw.lower() in node_name.lower() for kw in keywords):
                score = self._calculate_node_relevance(node, keywords)
                if node['id'] not in matched_node_ids:
                    results.append({
                        "id": f"node_{node['id']}",
                        "text": self._format_node_text(node),
                        "source": "knowledge_graph_node",
                        "original_data": node,
                        "relevance_score": score
                    })
                    matched_node_ids.add(node['id'])
        
        # 策略2：搜索相关关系
        for rel in self.rels:
            if self._matches_keywords_rel(rel, keywords):
                source_node = self.node_id_map.get(rel.get('source'))
                target_node = self.node_id_map.get(rel.get('target'))
                
                if source_node and target_node:
                    results.append({
                        "id": f"rel_{rel.get('id', len(results))}",
                        "text": self._format_relation_text(rel, source_node, target_node),
                        "source": "knowledge_graph_relation",
                        "original_data": rel,
                        "relevance_score": self._calculate_rel_relevance(rel, keywords)
                    })
        
        # 策略3：根据问题类型进行推理搜索
        if question_type == "出生地" and not self._has_birth_place(results):
            # 如果没有直接出生地，尝试用籍贯推理
            for node in self.nodes:
                if node['id'] in matched_node_ids:
                    props = node.get('props', {})
                    if props.get('籍贯'):
                        results.append({
                            "id": f"inference_birth_place",
                            "text": f"推理: {self._get_node_name(node)}的出生地可能是{props.get('籍贯')}（基于籍贯信息推理）",
                            "source": "knowledge_graph_inference",
                            "original_data": node,
                            "relevance_score": 3
                        })
        
        if question_type == "逝世地点" and not self._has_death_place(results):
            # 如果没有直接逝世地点，尝试用逝世时间和地点推理
            for node in self.nodes:
                if node['id'] in matched_node_ids:
                    props = node.get('props', {})
                    if props.get('逝世地点'):
                        results.append({
                            "id": f"inference_death_place",
                            "text": f"推理: {self._get_node_name(node)}的逝世地点是{props.get('逝世地点')}",
                            "source": "knowledge_graph_inference",
                            "original_data": node,
                            "relevance_score": 3
                        })
        
        # 按相关性排序
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return results[:top_k]

def _identify_question_type(self, query: str) -> str:
    """识别问题类型"""
    query_lower = query.lower()
    if '出生地' in query_lower or '出生地点' in query_lower:
        return '出生地'
    elif '逝世地点' in query_lower or '去世地点' in query_lower or '死在哪里' in query_lower:
        return '逝世地点'
    elif '籍贯' in query_lower:
        return '籍贯'
    elif '出生时间' in query_lower or '哪年出生' in query_lower:
        return '出生时间'
    elif '逝世时间' in query_lower or '哪年去世' in query_lower:
        return '逝世时间'
    else:
        return 'general'

def _has_birth_place(self, results: List[Dict]) -> bool:
    """检查是否有出生地信息"""
    for result in results:
        text = result.get('text', '')
        if '出生地' in text or '出生地点' in text:
            return True
    return False

def _has_death_place(self, results: List[Dict]) -> bool:
    """检查是否有逝世地点信息"""
    for result in results:
        text = result.get('text', '')
        if '逝世地点' in text or '去世地点' in text:
            return True
    return False
    
    def _format_node_text(self, node: Dict[str, Any]) -> str:
        """格式化节点为可读文本（适配两种数据格式）"""
        node_id = node.get('id', '?')
        labels = node.get('labels', [])
        props = node.get('props', {})
        
        # 获取节点名称
        node_name = self._get_node_name(node)
        
        # 构建描述
        parts = [f"实体: {node_name}"]
        parts.append(f"类型: {', '.join(labels)}")
        
        # 添加重要属性（最多5个）
        important_props = []
        for key, value in props.items():
            # 跳过名称字段
            if key in ['名称', '实体名称']:
                continue
            if value and len(str(value)) < 100:
                important_props.append(f"{key}: {value}")
        
        if important_props:
            parts.append("属性: " + " | ".join(important_props[:5]))
        
        return " | ".join(parts)
    
    def _format_relation_text(self, rel: Dict[str, Any], source_node: Dict, target_node: Dict) -> str:
        """格式化关系为可读文本"""
        rel_type = rel.get('type', '未知关系')
        rel_props = rel.get('props', {})
        
        source_name = self._get_node_name(source_node)
        target_name = self._get_node_name(target_node)
        
        desc = rel_props.get('描述', '')
        if desc:
            return f"关系: {source_name} --[{rel_type}]--> {target_name} ({desc})"
        else:
            return f"关系: {source_name} --[{rel_type}]--> {target_name}"
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取查询中的关键词"""
        try:
            import jieba
            # 使用jieba进行中文分词
            keywords = list(jieba.cut(query))
        except ImportError:
            # 如果没有jieba，就用正则提取中文词
            keywords = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]+', query)
        
        # 过滤掉常见停用词
        stopwords = {'的', '在', '是', '有', '和', '与', '及', '或', '等', '了', '也', '都', '并',
                     '问', '什么', '怎么', '吗', '呢', '啊', '呀', '哪个', '哪些', '哪里', '谁',
                     '可以', '一下', '这个', '那个', '这些', '那些', '一个', '一些', '一种',
                     '还有', '就是', '还是', '但是', '或者', '如果', '因为', '所以', '大连'}
        
        filtered = [kw.strip() for kw in keywords 
                   if len(kw.strip()) > 1 and kw.strip() not in stopwords]
        
        return filtered
    
    def _matches_keywords_rel(self, rel: Dict[str, Any], keywords: List[str]) -> bool:
        """检查关系是否匹配关键词"""
        rel_type = rel.get('type', '')
        rel_props = rel.get('props', {})
        desc = rel_props.get('描述', '')
        
        search_text = f"{rel_type} {desc}".lower()
        
        for kw in keywords:
            if kw.lower() in search_text:
                return True
        
        return False
    
    def _matches_keywords_in_props(self, node: Dict[str, Any], keywords: List[str]) -> bool:
        """检查节点属性中是否包含关键词"""
        props = node.get('props', {})
        
        for value in props.values():
            if isinstance(value, str):
                for kw in keywords:
                    if kw.lower() in value.lower():
                        return True
        
        return False
    
    def _matches_keywords_in_labels(self, node: Dict[str, Any], keywords: List[str]) -> bool:
        """检查节点标签中是否包含关键词"""
        labels = node.get('labels', [])
        
        for label in labels:
            if isinstance(label, str):
                for kw in keywords:
                    if kw.lower() in label.lower():
                        return True
        
        return False
    
    def _calculate_node_relevance(self, node: Dict[str, Any], keywords: List[str]) -> int:
        """计算节点与关键词的相关性得分"""
        score = 0
        node_name = self._get_node_name(node)
        node_name_lower = node_name.lower()
        
        for kw in keywords:
            # 完全匹配名称加分
            if kw.lower() == node_name_lower:
                score += 10
            # 名称中包含关键词加分
            elif kw.lower() in node_name_lower:
                score += 5
        
        return score
    
    def _calculate_rel_relevance(self, rel: Dict[str, Any], keywords: List[str]) -> int:
        """计算关系与关键词的相关性得分"""
        score = 0
        rel_type = rel.get('type', '')
        desc = rel.get('props', {}).get('描述', '')
        
        search_text = f"{rel_type} {desc}".lower()
        
        for kw in keywords:
            score += search_text.count(kw.lower()) * 3
        
        return score
    
    def get_node_by_id(self, node_id: int) -> Optional[Dict]:
        """根据ID获取节点"""
        return self.node_id_map.get(node_id)
    
    def get_relations_for_node(self, node_id: int) -> List[Dict]:
        """获取与节点相关的所有关系"""
        return self.node_relations.get(node_id, [])
    
    def expand_search(self, seed_nodes: List[int], depth: int = 1) -> List[Dict]:
        """从种子节点扩展搜索，获取相关实体"""
        results = []
        visited = set(seed_nodes)
        
        current_nodes = seed_nodes
        for _ in range(depth):
            next_nodes = []
            for node_id in current_nodes:
                relations = self.get_relations_for_node(node_id)
                for rel_info in relations:
                    if rel_info['type'] == 'outgoing':
                        target_id = rel_info['target_id']
                        if target_id and target_id not in visited:
                            target_node = self.node_id_map.get(target_id)
                            if target_node:
                                results.append({
                                    "id": f"node_{target_id}",
                                    "text": self._format_node_text(target_node),
                                    "source": "knowledge_graph_expanded",
                                    "original_data": target_node,
                                    "relevance_score": 2
                                })
                                visited.add(target_id)
                                next_nodes.append(target_id)
                    else:  # incoming
                        source_id = rel_info['source_id']
                        if source_id and source_id not in visited:
                            source_node = self.node_id_map.get(source_id)
                            if source_node:
                                results.append({
                                    "id": f"node_{source_id}",
                                    "text": self._format_node_text(source_node),
                                    "source": "knowledge_graph_expanded",
                                    "original_data": source_node,
                                    "relevance_score": 2
                                })
                                visited.add(source_id)
                                next_nodes.append(source_id)
            
            current_nodes = next_nodes
        
        return results

class QAPipeline:
    def __init__(self, 
                 deepseek_client: DeepSeekClient = None, 
                 llm_fn: Callable[[str], str] = None,
                 nodes_file: str = "kg_nodes.json",
                 rels_file: str = "kg_rels.json"):
        """
        初始化问答流水线
        
        Args:
            deepseek_client: DeepSeek客户端（可选）
            llm_fn: 大语言模型调用函数（可选）
            nodes_file: 知识图谱节点文件（默认 kg_nodes.json）
            rels_file: 知识图谱关系文件（默认 kg_rels.json）
        """
        self.client = deepseek_client
        self.llm_fn = llm_fn
        
        # 初始化本地知识图谱搜索器
        print(f"初始化知识图谱搜索器...")
        self.kg_searcher = LocalKnowledgeGraphSearcher(
            nodes_file_path=nodes_file,
            rels_file_path=rels_file
        )

    def _format_evidence(self, hits: List[Dict[str, Any]]) -> str:
        """格式化检索结果为证据文本"""
        lines = []
        for i, h in enumerate(hits, start=1):
            hid = h.get("id", f"证据_{i}")
            text = h.get("text", "")
            
            # 添加相关性提示
            if h.get("source") == "knowledge_graph_expanded":
                text = f"[相关扩展] {text}"
            
            # 截断避免太长
            text = text.replace("\n", " ")[:500]
            lines.append(f"[{hid}] {text}")
        
        # 添加数量统计
        if lines:
            lines.insert(0, f"共检索到 {len(hits)} 条相关证据：")
        
        return "\n\n".join(lines)

    def _compose_from_hits(self, hits: List[Dict[str, Any]]) -> str:
        """当没有LLM可用时，从检索结果合成简单回答"""
        if not hits:
            return "无法从知识图谱中找到相关信息。"
        
        parts = ["基于知识图谱检索到的信息："]
        seen = set()
        
        for h in hits[:5]:
            text = h.get("text", "")
            if text and text not in seen:
                parts.append(f"• {text}")
                seen.add(text)
        
        if len(parts) > 1:
            return "\n".join(parts)
        
        return "知识图谱中相关信息不完整。"

    def answer(self, 
               query: str, 
               top_k: int = 5, 
               use_llm: bool = True, 
               use_deepseek_chat: bool = False,
               expand_depth: int = 0) -> Dict[str, Any]:
        """
        回答问题
        
        Args:
            query: 用户问题
            top_k: 检索数量
            use_llm: 是否使用LLM生成答案
            use_deepseek_chat: 是否使用DeepSeek对话接口
            expand_depth: 扩展搜索深度（0表示不扩展）
        
        Returns:
            包含答案和证据的字典
        """
        # 1. 基础搜索
        kg_hits = self.kg_searcher.search(query, top_k)
        
        # 2. 如果需要扩展搜索
        if expand_depth > 0 and kg_hits:
            seed_nodes = []
            for hit in kg_hits:
                if hit.get('source') == 'knowledge_graph_node':
                    original = hit.get('original_data', {})
                    node_id = original.get('id')
                    if node_id is not None:
                        seed_nodes.append(node_id)
            
            if seed_nodes:
                expanded = self.kg_searcher.expand_search(seed_nodes, expand_depth)
                kg_hits.extend(expanded)
        
        # 3. 格式化证据
        evidence = self._format_evidence(kg_hits)
        
        # 4. 尝试使用DeepSeek Chat
        if use_deepseek_chat and self.client:
            try:
                full_prompt = PROMPT_TEMPLATE.format(query=query, evidence=evidence)
                resp = self.client.chat(prompt=full_prompt)
                
                if isinstance(resp, str):
                    answer_text = resp
                elif isinstance(resp, dict):
                    answer_text = (resp.get("answer") or 
                                 resp.get("generated_text") or 
                                 resp.get("result") or 
                                 str(resp))
                else:
                    answer_text = str(resp)
                
                return {
                    "answer": answer_text,
                    "evidence_hits": kg_hits,
                    "evidence_text": evidence
                }
                
            except Exception as e:
                print(f"DeepSeek调用失败: {e}")
        
        # 5. 使用提供的LLM
        if use_llm and self.llm_fn is not None:
            try:
                full_prompt = PROMPT_TEMPLATE.format(query=query, evidence=evidence)
                answer_text = self.llm_fn(full_prompt)
                
                return {
                    "answer": answer_text,
                    "evidence_hits": kg_hits,
                    "evidence_text": evidence
                }
            except Exception as e:
                print(f"LLM调用失败: {e}")
        
        # 6. 回退到合成回答
        answer_text = self._compose_from_hits(kg_hits)
        
        return {
            "answer": answer_text,
            "evidence_hits": kg_hits,
            "evidence_text": evidence
        }

def create_deepseek_llm_fn(client: DeepSeekClient) -> Callable[[str], str]:
    """创建DeepSeek LLM调用函数"""
    def deepseek_llm_fn(prompt: str) -> str:
        try:
            response = client.chat(prompt=prompt)
            if isinstance(response, str):
                return response
            elif isinstance(response, dict):
                return (response.get("answer") or 
                       response.get("generated_text") or 
                       response.get("result") or 
                       str(response))
            else:
                return str(response)
        except Exception as e:
            return f"[DeepSeek调用失败: {e}]"
    
    return deepseek_llm_fn


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="基于重构知识图谱的QA流水线")
    parser.add_argument("--query", type=str, default="大连有哪些红色旅游场馆？", help="查询问题")
    parser.add_argument("--top-k", type=int, default=5, help="检索数量")
    parser.add_argument("--expand-depth", type=int, default=1, help="扩展搜索深度")
    parser.add_argument("--nodes-file", type=str, default="kg_nodes.json", help="节点文件路径")
    parser.add_argument("--rels-file", type=str, default="kg_rels.json", help="关系文件路径")
    parser.add_argument("--no-llm", action="store_true", help="不使用LLM，只合成回答")
    parser.add_argument("--use-deepseek", action="store_true", help="使用DeepSeek生成回答")
    
    args = parser.parse_args()
    
    # 初始化DeepSeek客户端（如果需要）
    deepseek_client = None
    llm_fn = None
    
    if args.use_deepseek:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        base_url = os.environ.get("DEEPSEEK_BASE_URL")
        ds_model = os.environ.get("DEEPSEEK_MODEL")
        
        if api_key:
            deepseek_client = DeepSeekClient(
                api_key=api_key, 
                base_url=base_url, 
                model=ds_model
            )
            llm_fn = create_deepseek_llm_fn(deepseek_client)
            print("✓ DeepSeek客户端初始化成功")
        else:
            print("✗ 未找到DEEPSEEK_API_KEY，无法使用DeepSeek")
    
    # 初始化问答流水线
    pipeline = QAPipeline(
        deepseek_client=deepseek_client,
        llm_fn=llm_fn,
        nodes_file=args.nodes_file,
        rels_file=args.rels_file
    )
    
    print(f"\n🔍 查询: {args.query}")
    print(f"📊 参数: top_k={args.top_k}, expand_depth={args.expand_depth}")
    print(f"📁 数据文件: {args.nodes_file}, {args.rels_file}")
    print("-" * 60)
    
    # 执行问答
    result = pipeline.answer(
        query=args.query,
        top_k=args.top_k,
        use_llm=not args.no_llm,
        use_deepseek_chat=args.use_deepseek,
        expand_depth=args.expand_depth
    )
    
    # 输出结果
    print("\n📝 回答:")
    print(result["answer"])
    
    print("\n📋 使用证据:")
    for i, hit in enumerate(result["evidence_hits"][:3], 1):
        print(f"  {i}. {hit.get('id')}: {hit.get('text', '')[:100]}...")
    
    if len(result["evidence_hits"]) > 3:
        print(f"  ... 等共 {len(result['evidence_hits'])} 条证据")