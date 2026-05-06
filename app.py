from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import re
from pathlib import Path
import os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)  # 允许前端跨域请求

# 加载环境变量
load_dotenv()

# 加载知识图谱数据
def load_kg_data():
    nodes_file = Path('kg_nodes.json')
    rels_file = Path('kg_rels.json')
    
    nodes = []
    rels = []
    
    if nodes_file.exists():
        with open(nodes_file, 'r', encoding='utf-8') as f:
            nodes = json.load(f)
        print(f"✓ 加载了 {len(nodes)} 个节点")
    
    if rels_file.exists():
        with open(rels_file, 'r', encoding='utf-8') as f:
            rels = json.load(f)
        print(f"✓ 加载了 {len(rels)} 条关系")
    
    return nodes, rels


def entities_from_evidence_hits(hits, nodes):
    """从各类 evidence 命中里收集图谱实体 ID（关系、扩展、推理命中也纳入，便于子图高亮）"""
    node_by_id = {n['id']: n for n in nodes}
    out = []
    seen = set()

    def add_node(n):
        if not n or n.get('id') in seen:
            return
        props = n.get('props') or {}
        name = props.get('名称') or props.get('实体名称')
        if not name:
            return
        seen.add(n['id'])
        labels = n.get('labels') or ['未知']
        out.append({
            'id': n['id'],
            'name': name,
            'type': labels[0] if labels else '未知'
        })

    def add_node_id(nid):
        if nid is None:
            return
        add_node(node_by_id.get(nid))

    for hit in hits or []:
        src = hit.get('source')
        od = hit.get('original_data')
        if od:
            if src in ('knowledge_graph_node', 'knowledge_graph_expanded', 'knowledge_graph_inference'):
                add_node(od)
            elif src == 'knowledge_graph_relation':
                for nid in (od.get('source'), od.get('target')):
                    add_node_id(nid)
        hid = hit.get('id')
        if isinstance(hid, str):
            m = re.match(r'^node_(\d+)$', hid.strip(), re.I)
            if m:
                add_node_id(int(m.group(1)))
    return out


def augment_entities_from_free_text(text, nodes, existing):
    """
    从回答正文、证据串中识别图谱里存在的节点全称（含【】[] 内片段、顿号分隔），
    用于 LLM 回答里点名了场馆但 evidence_hits 未带 structured id 时仍能高亮子图。
    """
    if not text or not nodes:
        return []
    seen = {e['id'] for e in (existing or []) if e.get('id') is not None}
    out = []

    def try_add_node(n):
        if not n or n.get('id') in seen:
            return
        props = n.get('props') or {}
        name = props.get('名称') or props.get('实体名称')
        if not name:
            return
        seen.add(n['id'])
        labels = n.get('labels') or ['未知']
        out.append({
            'id': n['id'],
            'name': name,
            'type': labels[0] if labels else '未知'
        })

    indexed = []
    for n in nodes:
        props = n.get('props') or {}
        name = props.get('名称') or props.get('实体名称')
        if name and len(name) >= 2:
            indexed.append((len(name), name, n))
    indexed.sort(key=lambda x: -x[0])

    for _ln, name, node in indexed:
        if name in text:
            try_add_node(node)

    for m in re.finditer(r'[【\[]\s*([^\]】]+?)\s*[】\]]', text):
        frag = m.group(1).strip()
        if len(frag) < 2:
            continue
        for _ln, name, node in indexed:
            if frag in name or name in frag:
                try_add_node(node)
                break

    for line in text.splitlines():
        if '：' not in line and ':' not in line:
            continue
        if not re.search(r'场馆|景点|路线|涉及|推荐|博物馆|纪念|陵|塔|园|址|监狱|旧址', line):
            continue
        tail = line
        if '：' in line:
            tail = line.split('：', 1)[-1]
        elif ':' in line:
            tail = line.split(':', 1)[-1]
        for part in re.split(r'[、，,→]+', tail):
            part = re.sub(r'^[│\s├└─·]+|[│\s├└─·]+$', '', part).strip()
            if len(part) < 3:
                continue
            for _ln, name, node in indexed:
                if part in name or name in part:
                    try_add_node(node)
                    break

    return out


def merge_entity_lists(primary, extra):
    seen = set()
    out = []
    for e in (primary or []) + (extra or []):
        if not e or e.get('id') is None:
            continue
        if e['id'] in seen:
            continue
        seen.add(e['id'])
        out.append(e)
    return out


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'message': '服务器运行正常'})

@app.route('/api/graph', methods=['GET'])
def get_graph():
    """获取图谱数据"""
    nodes, rels = load_kg_data()
    
    # 转换为前端需要的格式
    graph_nodes = []
    for node in nodes:
        props = node.get('props', {})
        graph_nodes.append({
            'id': node['id'],
            'name': props.get('名称') or props.get('实体名称', f'节点_{node["id"]}'),
            'labels': node.get('labels', []),
            'props': props
        })
    
    graph_edges = []
    for rel in rels:
        graph_edges.append({
            'source': rel['source'],
            'target': rel['target'],
            'type': rel['type'],
            'props': rel.get('props', {})
        })
    
    return jsonify({
        'nodes': graph_nodes,
        'edges': graph_edges
    })

@app.route('/api/entity/<int:entity_id>', methods=['GET'])
def get_entity(entity_id):
    """获取实体详情"""
    nodes, rels = load_kg_data()
    
    # 查找节点
    node = next((n for n in nodes if n['id'] == entity_id), None)
    if not node:
        return jsonify({'error': 'Entity not found'}), 404
    
    # 查找相关关系
    relations = []
    for rel in rels:
        if rel['source'] == entity_id or rel['target'] == entity_id:
            source_node = next((n for n in nodes if n['id'] == rel['source']), None)
            target_node = next((n for n in nodes if n['id'] == rel['target']), None)
            
            if source_node and target_node:
                direction = 'outgoing' if rel['source'] == entity_id else 'incoming'
                relations.append({
                    'id': rel.get('id', len(relations)),
                    'type': rel['type'],
                    'direction': direction,
                    'source': {
                        'id': source_node['id'],
                        'name': source_node.get('props', {}).get('名称') or 
                                source_node.get('props', {}).get('实体名称', f'节点_{source_node["id"]}')
                    },
                    'target': {
                        'id': target_node['id'],
                        'name': target_node.get('props', {}).get('名称') or
                                target_node.get('props', {}).get('实体名称', f'节点_{target_node["id"]}')
                    },
                    'props': rel.get('props', {})
                })
    
    # 组装返回数据
    result = {
        'id': node['id'],
        'name': node.get('props', {}).get('名称') or 
                node.get('props', {}).get('实体名称', f'节点_{node["id"]}'),
        'labels': node.get('labels', []),
        'props': node.get('props', {}),
        'relations': relations
    }
    
    return jsonify(result)

@app.route('/api/qa/ask', methods=['POST'])
def ask_question():
    """问答接口（支持上下文）"""
    try:
        data = request.json
        query = data.get('query')
        top_k = data.get('top_k', 10)
        context = data.get('context', {})  # 获取上下文
        
        print(f"📝 收到问题: {query}")
        print(f"📚 上下文: {context}")
        
        # 这里调用你的 QA Pipeline
        try:
            from qa_pipeline import QAPipeline
            from deepseek_client import DeepSeekClient
            
            # 初始化
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            if api_key:
                client = DeepSeekClient(api_key=api_key)
                pipeline = QAPipeline(client)
                
                # 如果有上下文，增强查询（追问、代词、未再写出实体名时绑定上一话题实体）
                enhanced_query = query
                if context and context.get('lastEntity'):
                    last_entity = context.get('lastEntity')
                    entity_name = (
                        last_entity.get('name')
                        or (last_entity.get('props') or {}).get('名称')
                        or (last_entity.get('props') or {}).get('实体名称')
                    )
                    pronouns = ['他', '她', '它', '其', '这个', '那个', '这里', '那里']
                    followup_markers = (
                        '什么', '哪些', '怎么', '为何', '为什么', '干过', '做过', '事迹', '生平',
                        '介绍', '还有', '另外', '哪年', '在哪', '什么时候', '多大', '谁', '如何'
                    )
                    has_pronoun = any(p in query for p in pronouns)
                    looks_followup = any(m in query for m in followup_markers)
                    name_missing = entity_name and (entity_name not in query)
                    if entity_name and name_missing and (has_pronoun or looks_followup):
                        enhanced_query = f"{entity_name} {query}"
                        print(f"🔄 查询增强(上下文实体): {enhanced_query}")
                
                # 执行问答
                result = pipeline.answer(
                    query=enhanced_query,
                    top_k=top_k,
                    use_deepseek_chat=True,
                    expand_depth=2
                )
                
                nodes_kg, _ = load_kg_data()
                base_entities = entities_from_evidence_hits(result.get('evidence_hits'), nodes_kg)
                blob = '\n'.join([
                    str(result.get('answer') or ''),
                    str(result.get('evidence_text') or ''),
                ])
                for h in result.get('evidence_hits') or []:
                    blob += '\n' + str(h.get('text') or '')
                extra = augment_entities_from_free_text(blob, nodes_kg, base_entities)
                result['entities'] = merge_entity_lists(base_entities, extra)
                return jsonify(result)
            else:
                # 如果没有API key，返回模拟数据（基于知识图谱）
                nodes, _ = load_kg_data()
                
                # 简单的关键词匹配
                answer = "基于知识图谱查询结果：\n\n"
                evidence_hits = []
                entities = []
                
                for node in nodes[:5]:  # 只取前5个作为示例
                    node_name = node.get('props', {}).get('名称') or node.get('props', {}).get('实体名称', '')
                    if node_name and query in node_name:
                        answer += f"• {node_name}\n"
                        evidence_hits.append({
                            'id': f"node_{node['id']}",
                            'text': f"实体: {node_name}, 类型: {node.get('labels', ['未知'])[0]}"
                        })
                        entities.append({
                            'id': node['id'],
                            'name': node_name,
                            'type': node.get('labels', ['未知'])[0]
                        })
                
                if not evidence_hits:
                    answer = f"抱歉，没有找到与“{query}”直接相关的信息。"
                
                return jsonify({
                    'answer': answer,
                    'evidence_hits': evidence_hits,
                    'entities': entities
                })
                
        except ImportError as e:
            print(f"导入错误: {e}")
            # 返回模拟数据
            return jsonify({
                'answer': f'关于"{query}"的问题，正在查询知识图谱...',
                'evidence_hits': [
                    {'id': 'node_300', 'text': '实体: 关向应 | 类型: 红色人物 | 属性: 出生时间:1902年, 逝世时间:1946年'},
                    {'id': 'node_200', 'text': '实体: 关向应故居纪念馆 | 类型: 红色场馆 | 属性: 地址:金州区向应街道'}
                ],
                'entities': [
                    {'id': 300, 'name': '关向应', 'type': '红色人物'},
                    {'id': 200, 'name': '关向应故居纪念馆', 'type': '红色场馆'}
                ]
            })
            
    except Exception as e:
        print(f"❌ 问答接口错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_entities():
    """搜索实体"""
    keyword = request.args.get('keyword', '')
    nodes, _ = load_kg_data()
    
    results = []
    for node in nodes:
        name = node.get('props', {}).get('名称') or node.get('props', {}).get('实体名称', '')
        if keyword.lower() in name.lower():
            results.append({
                'id': node['id'],
                'name': name,
                'type': node.get('labels', ['未知'])[0]
            })
    
    return jsonify(results[:10])  # 最多返回10条

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取图谱统计信息"""
    nodes, rels = load_kg_data()
    
    # 统计节点类型
    type_count = {}
    for node in nodes:
        labels = node.get('labels', ['未知'])
        for label in labels:
            type_count[label] = type_count.get(label, 0) + 1
    
    # 统计关系类型
    rel_type_count = {}
    for rel in rels:
        rel_type = rel.get('type', '未知')
        rel_type_count[rel_type] = rel_type_count.get(rel_type, 0) + 1
    
    return jsonify({
        'total_nodes': len(nodes),
        'total_relations': len(rels),
        'node_types': type_count,
        'relation_types': rel_type_count
    })

@app.route('/')
def index():
    """根路径返回API信息"""
    return jsonify({
        'name': '大连红色旅游知识图谱API',
        'version': '1.0',
        'endpoints': [
            '/api/health - 健康检查',
            '/api/graph - 获取图谱数据',
            '/api/entity/<id> - 获取实体详情',
            '/api/qa/ask - 问答接口（支持上下文）',
            '/api/search - 搜索实体',
            '/api/stats - 统计信息'
        ],
        'frontend': '请访问 http://localhost:8080 使用前端界面'
    })

if __name__ == '__main__':
    print("🚀 启动知识图谱后端服务...")
    print("📁 数据文件: kg_nodes.json, kg_rels.json")
    print("🌐 API地址: http://localhost:5000")
    print("📝 可用接口:")
    print("   GET  /api/health      - 健康检查")
    print("   GET  /api/graph       - 获取图谱数据")
    print("   GET  /api/entity/<id> - 获取实体详情")
    print("   POST /api/qa/ask      - 问答接口（支持上下文）")
    print("   GET  /api/search      - 搜索实体")
    print("   GET  /api/stats       - 统计信息")
    print("-" * 50)
    app.run(debug=True, port=5000)