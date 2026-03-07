import json
import pandas as pd

# 直接读取预处理JSON，生成节点和关系CSV
with open("大连红色旅游三元组_预处理.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 生成节点CSV（实体+属性）
node_properties = {}
for item in data:
    if item["数据类型"] == "实体-属性-属性值":
        entity = item["主体"]
        if entity not in node_properties:
            node_properties[entity] = {"实体名称": entity, "分类": item["分类"]}
        node_properties[entity][item["属性"]] = item["属性值"]
pd.DataFrame(node_properties.values()).to_csv("大连红色旅游_节点.csv", index=False, encoding="utf-8-sig")

# 生成关系CSV（实体-关系-实体）
relations = []
for item in data:
    if item["数据类型"] == "实体-关系-实体":
        relations.append({
            "起始节点": item["主体"],
            "关系类型": item["关系"],
            "目标节点": item["客体"]
        })
pd.DataFrame(relations).to_csv("大连红色旅游_关系.csv", index=False, encoding="utf-8-sig")

print("直接生成CSV完成")