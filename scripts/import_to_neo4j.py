"""
将 aligned_entities.csv 和 relationships.csv 导入 Neo4j 图数据库。

- aligned_entities.csv: entity_name, entity_type, frequency → 创建节点
- relationships.csv: head, relation, tail → 创建关系边

分类要求：红色人物、红色场馆、地理位置、历史事件、时间节点
"""

from neo4j import GraphDatabase
import pandas as pd
import os
import sys

# ============== Neo4j 连接配置 ==============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "yanmj20040627"

# ============== CSV 文件路径 ==============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENTITIES_CSV = os.path.join(SCRIPT_DIR, "aligned_entities.csv")
RELATIONSHIPS_CSV = os.path.join(SCRIPT_DIR, "relationships.csv")


def clear_database(driver):
    """清空数据库中所有节点和关系（可选，谨慎使用）"""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("[Success] Database cleared")


def create_constraints(driver):
    """为五个标准分类分别创建唯一性约束"""
    STD_TYPES = ["红色人物", "红色场馆", "地理位置", "历史事件", "时间节点"]
    with driver.session() as session:
        for label in STD_TYPES:
            try:
                # Neo4j 4.x+ 语法
                session.run(f"CREATE CONSTRAINT {label}_name_unique IF NOT EXISTS FOR (n:`{label}`) REQUIRE n.name IS UNIQUE")
                print(f"[Success] Constraint created: {label}")
            except Exception:
                try:
                    # 旧版本语法兼容
                    session.run(f"CREATE CONSTRAINT ON (n:`{label}`) ASSERT n.name IS UNIQUE")
                    print(f"[Success] Constraint created: {label} (Old syntax)")
                except Exception as e:
                    print(f"[Warning] Constraint {label} skipped: {e}")


def import_entities(driver, csv_path):
    """
    导入实体节点。
    每个实体拥有两个标签：通用标签 `实体` + 具体类型标签（如 `红色人物`、`红色场馆`）。
    属性包含：name（实体名称）、frequency（出现频率）。
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"\n📥 开始导入实体节点，共 {len(df)} 条记录...")

    success_count = 0
    skip_count = 0

    # 标准分类定义
    STD_TYPES = ["红色人物", "红色场馆", "地理位置", "历史事件", "时间节点"]
    TYPE_MAPPING = {
        "地点": "地理位置",
        "组织机构": "历史事件",
        "时间": "时间节点"
    }

    def normalize_type(raw_t):
        if raw_t in STD_TYPES:
            return raw_t
        return TYPE_MAPPING.get(raw_t, "历史事件")

    with driver.session() as session:
        for _, row in df.iterrows():
            entity_name = str(row["entity_name"]).strip()
            raw_type = str(row["entity_type"]).strip()
            frequency = int(row["frequency"])

            # 规范化类型
            entity_type = normalize_type(raw_type)

            # 跳过空实体名
            if not entity_name:
                skip_count += 1
                continue

            # 使用 MERGE 避免重复创建
            # 移除 :实体 标签，直接使用具体分类标签
            cypher = f"""
                MERGE (e:`{entity_type}` {{name: $name}})
                ON CREATE SET e.frequency = $freq, e.raw_type = $raw_type
                ON MATCH SET e.frequency = e.frequency + $freq
            """
            try:
                session.run(cypher, name=entity_name, freq=frequency, raw_type=raw_type)
                success_count += 1
            except Exception as e:
                print(f"  [Error] Failed to import [{entity_name}]: {e}")

    print(f"[Success] Entities imported: {success_count} success, {skip_count} skipped")


def import_relationships(driver, csv_path):
    """
    导入关系边。
    根据 head 和 tail 匹配已有节点，创建带有关系类型的边。
    如果 head 或 tail 在节点中不存在，则自动创建为 `实体` 类型节点。
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"\n📥 开始导入关系边，共 {len(df)} 条记录...")

    success_count = 0
    fail_count = 0

    with driver.session() as session:
        for _, row in df.iterrows():
            head = str(row["head"]).strip()
            relation = str(row["relation"]).strip()
            tail = str(row["tail"]).strip()

            # 跳过空值
            if not head or not tail or not relation:
                fail_count += 1
                continue

            # 清理关系类型名称（Neo4j 关系类型不能包含 `/` 等特殊字符）
            safe_relation = relation.replace("/", "_").replace(" ", "_")

            # 使用 MERGE 确保头尾节点存在
            # 移除 :实体 标签，使用无标签匹配以寻找已有节点
            cypher = f"""
                MERGE (h {{name: $head}})
                MERGE (t {{name: $tail}})
                CREATE (h)-[r:`{safe_relation}` {{relation_name: $rel_name}}]->(t)
            """
            try:
                session.run(cypher, head=head, tail=tail, rel_name=relation)
                success_count += 1
            except Exception as e:
                print(f"  [Error] Failed to create relationship [{head} -[{relation}]-> {tail}]: {e}")
                fail_count += 1

    print(f"[Success] Relationships imported: {success_count} success, {fail_count} failed")


def print_statistics(driver):
    """打印导入后的数据库统计信息"""
    print("\n" + "=" * 50)
    print("📊 Neo4j 数据库统计")
    print("=" * 50)

    with driver.session() as session:
        # 节点总数
        result = session.run("MATCH (n) RETURN count(n) AS cnt")
        node_count = result.single()["cnt"]
        print(f"  节点总数: {node_count}")

        # 关系总数
        result = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
        rel_count = result.single()["cnt"]
        print(f"  关系总数: {rel_count}")

        # 按标签统计节点
        result = session.run("""
            MATCH (n) 
            UNWIND labels(n) AS label 
            RETURN label, count(*) AS cnt 
            ORDER BY cnt DESC
        """)
        print("\n  节点标签分布:")
        for record in result:
            print(f"    - {record['label']}: {record['cnt']}")

        # 按类型统计关系
        result = session.run("""
            MATCH ()-[r]->() 
            RETURN type(r) AS rel_type, count(*) AS cnt 
            ORDER BY cnt DESC
        """)
        print("\n  关系类型分布:")
        for record in result:
            print(f"    - {record['rel_type']}: {record['cnt']}")

    print("=" * 50)


def main():
    """主函数：连接 Neo4j 并执行导入"""
    print("=" * 50)
    print("Dalian Red Tourism KG -> Neo4j Import Tool")
    print("=" * 50)

    # 检查 CSV 文件是否存在
    if not os.path.exists(ENTITIES_CSV):
        print(f"[Error] File not found: {ENTITIES_CSV}")
        sys.exit(1)
    if not os.path.exists(RELATIONSHIPS_CSV):
        print(f"[Error] File not found: {RELATIONSHIPS_CSV}")
        sys.exit(1)

    # 连接 Neo4j
    print(f"\nConnecting to Neo4j: {NEO4J_URI}")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        # 验证连接
        driver.verify_connectivity()
        print("[Success] Connected to Neo4j")

        # 询问是否清空数据库
        user_input = input("\n[Warning] Clear database before import? (y/N): ").strip().lower()
        if user_input == "y":
            clear_database(driver)

        # 创建约束
        create_constraints(driver)

        # 导入实体节点
        import_entities(driver, ENTITIES_CSV)

        # 导入关系边
        import_relationships(driver, RELATIONSHIPS_CSV)

        # 打印统计信息
        print_statistics(driver)

        print("\n[Done] Import complete! View in Neo4j Browser (http://localhost:7474).")
        print("   Query example: MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50")

    except Exception as e:
        print(f"\n[Error] Exception occurred: {e}")
        sys.exit(1)
    finally:
        driver.close()
        print("\nConnection closed")


if __name__ == "__main__":
    main()
