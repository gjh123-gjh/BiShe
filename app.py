from flask import Flask, request, jsonify
from flask_cors import CORS
import json
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
        top_k = data.get('top_k', 5)
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
                
                # 如果有上下文，增强查询
                enhanced_query = query
                if context and context.get('lastEntity'):
                    last_entity = context.get('lastEntity')
                    entity_name = last_entity.get('name') or last_entity.get('props', {}).get('名称')
                    
                    # 检查是否是指代性问题
                    pronouns = ['他', '她', '它', '其', '这个', '那个', '这里', '那里']
                    if any(p in query for p in pronouns) and entity_name:
                        # 构建更精确的查询
                        enhanced_query = f"{entity_name} {query}"
                        print(f"🔄 查询增强: {enhanced_query}")
                
                # 执行问答
                result = pipeline.answer(
                    query=enhanced_query,
                    top_k=top_k,
                    use_deepseek_chat=True,
                    expand_depth=1
                )
                
                # 从证据中提取实体
                entities = []
                for hit in result.get('evidence_hits', []):
                    if hit.get('source') == 'knowledge_graph_node':
                        original = hit.get('original_data')
                        if original:
                            entity_name = original.get('props', {}).get('名称') or original.get('props', {}).get('实体名称')
                            if entity_name:
                                entities.append({
                                    'id': original.get('id'),
                                    'name': entity_name,
                                    'type': original.get('labels', ['未知'])[0]
                                })
                
                result['entities'] = entities
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