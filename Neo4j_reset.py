from neo4j import GraphDatabase
import json

class Neo4jUpdater:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """清空数据库"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("数据库已清空")
    
    def create_constraints(self):
        """创建约束和索引"""
        with self.driver.session() as session:
            # 创建约束
            session.run("CREATE CONSTRAINT node_id_unique IF NOT EXISTS FOR (n:Node) REQUIRE n.id IS UNIQUE")
            
            # 创建索引
            session.run("CREATE INDEX person_name_index IF NOT EXISTS FOR (p:红色人物) ON (p.名称)")
            session.run("CREATE INDEX venue_name_index IF NOT EXISTS FOR (v:红色场馆) ON (v.名称)")
            session.run("CREATE INDEX event_name_index IF NOT EXISTS FOR (e:历史事件) ON (e.名称)")
            
            print("约束和索引已创建")
    
    def import_nodes(self, nodes_file):
        """导入节点"""
        with open(nodes_file, 'r', encoding='utf-8') as f:
            nodes = json.load(f)
        
        with self.driver.session() as session:
            for node in nodes:
                # 构建Cypher查询
                labels_str = ":".join(node['labels'])
                props = {**node['props'], 'id': node['id']}
                
                query = f"""
                CREATE (n:{labels_str} $props)
                RETURN n
                """
                
                session.run(query, props=props)
            
            print(f"已导入 {len(nodes)} 个节点")
    
    def import_relationships(self, edges_file):
        """导入关系"""
        with open(edges_file, 'r', encoding='utf-8') as f:
            edges = json.load(f)
        
        with self.driver.session() as session:
            for edge in edges:
                query = """
                MATCH (source {id: $source_id})
                MATCH (target {id: $target_id})
                CREATE (source)-[r:%s $props]->(target)
                RETURN r
                """ % edge['type']
                
                params = {
                    'source_id': edge['source'],
                    'target_id': edge['target'],
                    'props': edge.get('props', {})
                }
                
                session.run(query, params)
            
            print(f"已导入 {len(edges)} 条关系")
    
    def validate_data(self):
        """验证数据"""
        with self.driver.session() as session:
            # 节点统计
            result = session.run("""
            MATCH (n) 
            RETURN labels(n) AS labels, count(*) AS count 
            ORDER BY count DESC
            """)
            
            print("=== 节点统计 ===")
            for record in result:
                print(f"{record['labels']}: {record['count']}")
            
            # 关系统计
            result = session.run("""
            MATCH ()-[r]->() 
            RETURN type(r) AS type, count(*) AS count 
            ORDER BY count DESC
            """)
            
            print("\n=== 关系统计 ===")
            for record in result:
                print(f"{record['type']}: {record['count']}")

# 使用示例
if __name__ == "__main__":
    # Neo4j连接配置
    URI = "bolt://localhost:7687"
    USER = "neo4j"
    PASSWORD = "yanmj20040627"
    
    # 文件路径
    NODES_FILE = "kg_nodes.json"
    EDGES_FILE = "kg_rels.json"
    
    # 创建更新器
    updater = Neo4jUpdater(URI, USER, PASSWORD)
    
    try:
        # 1. 清空数据库（可选）
        # updater.clear_database()
        
        # 2. 创建约束
        updater.create_constraints()
        
        # 3. 导入节点
        updater.import_nodes(NODES_FILE)
        
        # 4. 导入关系
        updater.import_relationships(EDGES_FILE)
        
        # 5. 验证
        updater.validate_data()
        
    finally:
        updater.close()