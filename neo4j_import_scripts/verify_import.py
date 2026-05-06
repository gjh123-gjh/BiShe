from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "yanmj20040627"

def verify():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        print("--- 节点统计 ---")
        # 改为通过属性 '所属项目' 进行统计
        result = session.run("MATCH (n) WHERE n.所属项目 = '红色旅游' RETURN labels(n) as labels, count(n) as count")
        for record in result:
            print(f"标签: {record['labels']}, 数量: {record['count']}")
        
        print("\n--- 关系统计 ---")
        result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
        for record in result:
            print(f"关系类型: {record['type']}, 数量: {record['count']}")
            
    driver.close()

if __name__ == "__main__":
    verify()
