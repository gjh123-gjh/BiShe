import pandas as pd
from neo4j import GraphDatabase
import os

# Neo4j 连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "yanmj20040627"

# 文件路径配置
# 脚本位于 d:/BiShe/neo4j_import_scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODES_CSV = os.path.join(BASE_DIR, "scripts", "extracted_entities.csv")
RELS_CSV = os.path.join(BASE_DIR, "scripts", "relationships.csv")

class Neo4jImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def import_nodes(self, csv_path):
        """导入节点数据"""
        print(f"正在从 {csv_path} 导入节点...")
        # 显式指定编码方式，防止乱码
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        with self.driver.session() as session:
            for _, row in df.iterrows():
                # 提取属性，过滤空值
                name = row['entity_name']
                label = row['entity_type']
                freq = row['frequency']
                
                # 使用 MERGE 保证幂等性
                # 方案 B：移除 ':红色旅游' 标签，改为属性存储
                cypher = f"""
                MERGE (n:`{label}` {{实体名称: $name}})
                SET n.frequency = $frequency,
                    n.所属项目 = "红色旅游"
                """
                session.run(cypher, name=name, frequency=freq)
        print(f"节点导入完成，共处理 {len(df)} 行数据。")

    def import_relationships(self, csv_path):
        """导入关系数据"""
        print(f"正在从 {csv_path} 导入关系...")
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        with self.driver.session() as session:
            for _, row in df.iterrows():
                head = row['head']
                rel_type = row['relation']
                tail = row['tail']
                
                if pd.isna(head) or pd.isna(tail) or pd.isna(rel_type):
                    continue

                # 匹配起始和目标节点
                # 使用反引号包裹关系类型，以支持特殊字符（如 '/'）
                cypher = f"""
                MATCH (a:`红色旅游` {{实体名称: $head}})
                MATCH (b:`红色旅游` {{实体名称: $tail}})
                MERGE (a)-[r:`{rel_type}`]->(b)
                """
                session.run(cypher, head=head, tail=tail)
        print(f"关系导入完成，共处理 {len(df)} 行数据。")

if __name__ == "__main__":
    # 检查文件是否存在
    if not os.path.exists(NODES_CSV):
        print(f"错误: 找不到节点文件 {NODES_CSV}")
    elif not os.path.exists(RELS_CSV):
        print(f"错误: 找不到关系文件 {RELS_CSV}")
    else:
        importer = Neo4jImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        try:
            importer.import_nodes(NODES_CSV)
            importer.import_relationships(RELS_CSV)
            print("\n[成功] 数据导入完成！")
        except Exception as e:
            print(f"\n[错误] 导入过程中出现异常: {e}")
        finally:
            importer.close()
