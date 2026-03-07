"""
离线演示：QA 流程的模拟版本（不调用真实 API，直接用样本数据演示）
使用本地知识图谱的节点数据作为"检索结果"
"""
import json
from pathlib import Path
from typing import Dict, Any, List

# 加载知识图谱节点数据（如果存在）
def load_sample_nodes():
    """尝试加载本地导出的节点数据"""
    candidates = [
        Path("d:/BiShe/data_LaJi/kg_nodes.json"),
        Path("d:/BiShe/kg_nodes.json"),
    ]
    
    for path in candidates:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
    
    # 如果没有真实数据，使用样本数据
    return [
        {
            "id": "n1",
            "name": "旅顺口战役遗址",
            "type": "红色场馆",
            "description": "大连著名的红色旅游景点，展示了1945年的历史"
        },
        {
            "id": "n2",
            "name": "周恩来",
            "type": "红色人物",
            "description": "中华人民共和国的杰出领导人，为国家做出了巨大贡献"
        },
        {
            "id": "n3",
            "name": "解放战争",
            "type": "历史事件",
            "description": "中国人民解放军推翻国民党政权的伟大事业"
        },
    ]

def format_evidence(nodes: List[Dict[str, Any]]) -> str:
    """格式化节点为证据文本"""
    lines = []
    for i, node in enumerate(nodes[:5], start=1):
        name = node.get("name") or node.get("实体名称") or f"节点_{node.get('id')}"
        desc = node.get("description") or node.get("描述") or ""
        ntype = node.get("type") or node.get("分类") or ""
        
        text = f"{name}"
        if ntype:
            text += f"（{ntype}）"
        if desc:
            text += f": {desc}"
        lines.append(f"[{node.get('id')}] {text}")
    
    return "\n\n".join(lines)

def simulate_llm_response(prompt: str) -> str:
    """模拟 LLM 的回答（仅用于演示）"""
    if "红色旅游场馆" in prompt or "场馆" in prompt:
        return (
            "根据证据，大连有以下红色旅游场馆：\n"
            "- 旅顺口战役遗址（文献 [n1]）：一个展示1945年历史的著名红色景点\n\n"
            "这个场馆记录了解放战争时期的重要历史事件。"
        )
    elif "红色人物" in prompt or "人物" in prompt:
        return (
            "根据证据记载，周恩来（文献 [n2]）是中华人民共和国的杰出领导人，"
            "为国家做出了巨大贡献。"
        )
    else:
        return (
            "根据检索到的证据，我无法准确回答这个问题。"
            "请提供更具体的查询条件。"
        )

PROMPT_TEMPLATE = (
    "你是一个知识检索助手。使用下面的证据回答用户问题。"
    "严格基于证据回答，若证据不足请说明：无法从现有证据确定。\n\n"
    "问题：{query}\n\n"
    "证据：\n{evidence}\n\n"
    "请给出简明答案，并在末尾列出用于支持答案的证据项 id（最多 5 条）。"
)

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 QA 流程离线演示（模拟版本）")
    print("=" * 60)
    
    # 加载数据
    nodes = load_sample_nodes()
    print(f"\n✓ 已加载 {len(nodes)} 个知识图谱节点")
    
    # 示例查询
    queries = [
        "大连有哪些红色旅游场馆？",
        "周恩来是谁？",
        "解放战争发生在什么时候？"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'-' * 60}")
        print(f"【查询 {i}】{query}")
        print(f"{'-' * 60}")
        
        # 模拟检索（本例中就用所有节点）
        retrieved_nodes = nodes
        evidence = format_evidence(retrieved_nodes)
        
        # 拼接 prompt
        prompt = PROMPT_TEMPLATE.format(query=query, evidence=evidence)
        print(f"\n📄 检索到的证据：\n{evidence}")
        
        # 生成回答
        answer = simulate_llm_response(prompt)
        print(f"\n💬 LLM 回答：\n{answer}")
    
    print("\n" + "=" * 60)
    print("✅ 离线演示完成！")
    print("\n💡 要使用真实的 API：")
    print("   1. 检查网络连接和代理设置")
    print("   2. 运行：python qa_pipeline.py")
    print("=" * 60)
