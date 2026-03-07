"""
完整的 QA 演示：展示从知识图谱中检索并生成答案的完整流程
（当网络无法连接时使用）
"""
import json
from pathlib import Path
from typing import List, Dict, Any

PROMPT_TEMPLATE = (
    "你是一个知识检索助手。使用下面的证据回答用户问题。"
    "严格基于证据回答，若证据不足请说明：无法从现有证据确定。\n\n"
    "问题：{query}\n\n"
    "证据：\n{evidence}\n\n"
    "请给出简明答案，并在末尾列出用于支持答案的证据项 id（最多 5 条）。"
)

def load_kg_nodes():
    """加载知识图谱节点"""
    candidates = [
        Path("data_LaJi/kg_nodes.json"),
        Path("kg_nodes.json"),
    ]
    
    for path in candidates:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠ 加载 {path} 失败: {e}")
    
    return []

def search_nodes(query: str, nodes: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """简单的关键词匹配检索（演示用）"""
    results = []
    query_words = set(query.lower().split())
    
    for node in nodes:
        # 从 props 中提取名称和描述
        props = node.get('props', {}) if isinstance(node.get('props'), dict) else {}
        name = props.get('实体名称', '').lower()
        labels = node.get('labels', [])
        
        # 计算匹配分数
        score = 0
        for word in query_words:
            if word in name:
                score += 2
            for label in labels:
                if isinstance(label, str) and word in label.lower():
                    score += 1
        
        if score > 0:
            results.append((node, score))
    
    # 按分数排序并返回 top-k
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results[:top_k]]

def format_evidence(hits: List[Dict[str, Any]]) -> str:
    """格式化检索结果为证据文本"""
    lines = []
    for h in hits:
        nid = h.get('id', '?')
        props = h.get('props', {}) if isinstance(h.get('props'), dict) else {}
        name = props.get('实体名称', f'节点_{nid}')
        labels = h.get('labels', [])
        
        text = f"{name}"
        if labels:
            text += f"（{'/'.join(str(l) for l in labels)}）"
        
        lines.append(f"[{nid}] {text}")
    
    return "\n\n".join(lines)

def simulate_qa(query: str, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """模拟 QA 流程"""
    # 检索
    hits = search_nodes(query, nodes, top_k=5)
    evidence = format_evidence(hits)
    
    # 生成答案（这里是简单规则，实际应该调用 LLM）
    if not hits:
        answer = "抱歉，我在知识库中找不到相关信息来回答这个问题。"
    else:
        hit_names = [h.get('props', {}).get('实体名称', '') for h in hits]
        names_str = "、".join([n for n in hit_names if n])
        answer = f"根据检索到的知识，相关的实体有：{names_str}。" if names_str else "未能生成明确的答案。"
    
    return {
        "query": query,
        "evidence_count": len(hits),
        "evidence": evidence,
        "answer": answer,
        "hits": hits
    }

if __name__ == "__main__":
    print("=" * 80)
    print("📚 知识图谱问答系统 - 离线演示")
    print("=" * 80)
    
    # 加载知识图谱
    nodes = load_kg_nodes()
    if not nodes:
        print("✗ 无法加载知识图谱数据")
        exit(1)
    
    print(f"\n✓ 已加载 {len(nodes)} 个知识图谱节点")
    print(f"   节点范围: id = 0 到 {len(nodes)-1}")
    
    # 示例查询
    sample_queries = [
        "大连有哪些红色旅游场馆？",
        "旅顺大屠杀",
        "1926年发生了什么？",
        "红色展品",
        "旅顺",
    ]
    
    print("\n" + "=" * 80)
    print("【示例查询】")
    print("=" * 80)
    
    for i, query in enumerate(sample_queries, 1):
        print(f"\n【查询 {i}】{query}")
        print("-" * 80)
        
        result = simulate_qa(query, nodes)
        
        print(f"\n📄 检索到 {result['evidence_count']} 个相关节点：")
        print(result['evidence'])
        
        print(f"\n💬 生成的答案：")
        print(result['answer'])
        
        if i < len(sample_queries):
            print()
    
    # 交互式查询
    print("\n" + "=" * 80)
    print("【交互式模式】")
    print("=" * 80)
    print("\n你可以输入自己的查询问题（输入 'quit' 退出）：\n")
    
    while True:
        user_query = input(">>> 输入问题：").strip()
        if user_query.lower() in ('quit', 'exit', 'q'):
            print("\n再见！")
            break
        
        if not user_query:
            continue
        
        result = simulate_qa(user_query, nodes)
        
        print(f"\n📄 检索到 {result['evidence_count']} 个相关节点：")
        print(result['evidence'])
        
        print(f"\n💬 生成的答案：")
        print(result['answer'])
        print()
