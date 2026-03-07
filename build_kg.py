from Neo4j_red import driver
import json
import re

def sanitize_label(s):
    return re.sub(r"\W+", "_", s.replace("类", "")).strip("_") or "默认分类"

def sanitize_rel(s):
    return re.sub(r"\W+", "_", s).strip("_") or "关联"

def build_graph(preprocessed_json_path):
    with open(preprocessed_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with driver.session() as session:
        for item in data:
            if item.get("数据类型") == "实体-属性-属性值":
                ent = item["主体"]
                attr = item["属性"]
                val = item["属性值"]
                label = sanitize_label(item.get("分类", "默认分类"))

                # 创建/合并实体节点
                cypher_ent = f"""
                MERGE (e:`红色旅游`:`{label}` {{实体名称: $ent}})
                SET e.分类 = $orig_cat
                """
                session.run(cypher_ent, ent=ent, orig_cat=item.get("分类", ""))

                # 创建/合并属性节点
                cypher_prop = "MERGE (p:Property {属性: $attr, 值: $val})"
                session.run(cypher_prop, attr=attr, val=val)

                # 连接实体与属性节点
                cypher_link = """
                MATCH (e:`红色旅游` {实体名称: $ent})
                MATCH (p:Property {属性: $attr, 值: $val})
                MERGE (e)-[r:HAS_PROPERTY {属性: $attr}]->(p)
                """
                session.run(cypher_link, ent=ent, attr=attr, val=val)

            elif item.get("数据类型") == "实体-关系-实体":
                a = item["主体"]
                rel = item["关系"]
                b = item["客体"]
                label_a = sanitize_label(item.get("分类", "默认分类"))
                label_b = sanitize_label(item.get("分类", "默认分类"))
                rel_type = sanitize_rel(rel).upper()

                # 创建/合并两个实体节点（分别设置分类标签）
                cypher_merge_nodes = f"""
                MERGE (x:`红色旅游`:`{label_a}` {{实体名称: $a}})
                MERGE (y:`红色旅游`:`{label_b}` {{实体名称: $b}})
                """
                session.run(cypher_merge_nodes, a=a, b=b)

                # 创建关系（关系类型已消毒）
                cypher_rel = f"""
                MATCH (x:`红色旅游` {{实体名称: $a}})
                MATCH (y:`红色旅游` {{实体名称: $b}})
                MERGE (x)-[r:`{rel_type}` {{原关系: $orig_rel}}]->(y)
                """
                session.run(cypher_rel, a=a, b=b, orig_rel=rel)

    print("知识图谱构建完成（已将属性作为节点并创建关系）。")


if __name__ == '__main__':
    build_graph("大连红色旅游三元组_预处理.json")
