from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "yanmj20040627"

def fix_labels():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        print("正在清理 '红色旅游' 标签并转换为属性...")
        # 移除标签 '红色旅游'，并确保所有节点都有 '所属项目' 属性
        query = """
        MATCH (n:红色旅游)
        REMOVE n:红色旅游
        SET n.所属项目 = "红色旅游"
        RETURN count(n) as count
        """
        result = session.run(query)
        record = result.single()
        print(f"成功处理了 {record['count']} 个节点。")
    driver.close()

if __name__ == "__main__":
    try:
        fix_labels()
        print("清理完成！")
    except Exception as e:
        print(f"清理过程中出错: {e}")
