from neo4j import GraphDatabase
import pandas as pd

# Neo4j配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "yanmj20040627"  # 替换为你的密码

# 连接数据库
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def import_nodes(node_csv_path):
    """导入节点数据（无实体类型列，使用分类作为标签）"""
    node_df = pd.read_csv(node_csv_path, encoding="utf-8-sig")
    with driver.session() as session:
        for _, row in node_df.iterrows():
            # 构建属性字典（过滤空值）
            properties = {k: v for k, v in row.items() if pd.notna(v) and v != ""}

            # 提取"分类"作为标签（如"红色场馆类"），替换特殊字符
            category = properties.get("分类", "默认分类").replace("类", "").replace(" ", "_")

            # 构建Cypher语句：标签为"红色旅游"+分类（如:红色旅游:红色场馆）
            cypher = f"""
            CREATE (n:`红色旅游`:`{category}` $properties)
            """
            session.run(cypher, properties=properties)
    print(f"节点导入完成，共导入{len(node_df)}个节点")


def import_relations(relation_csv_path):
    """导入关系数据（适配节点CSV的结构）"""
    relation_df = pd.read_csv(relation_csv_path, encoding="utf-8-sig")
    with driver.session() as session:
        for _, row in relation_df.iterrows():
            # 关系属性（可根据CSV列名调整）
            rel_properties = {
                "来源": row.get("来源", "红色旅游数据"),
                "分类": row.get("分类", "")
            }

            # 构建Cypher语句：匹配起始节点和目标节点，创建关系
            cypher = """
            MATCH (a:`红色旅游` {实体名称: $start_node})
            MATCH (b:`红色旅游` {实体名称: $end_node})
            CREATE (a)-[r:`%s` $rel_props]->(b)
            """ % row["关系类型"]  # 关系类型从CSV的"关系类型"列获取

            session.run(
                cypher,
                start_node=row["起始节点"],
                end_node=row["目标节点"],
                rel_props=rel_properties
            )
    print(f"关系导入完成，共导入{len(relation_df)}条关系")


# 执行导入
if __name__ == "__main__":
    import_nodes("大连红色旅游_节点.csv")  # 你的节点CSV路径
    import_relations("大连红色旅游_关系.csv")  # 你的关系CSV路径
    driver.close()  # 关闭连接