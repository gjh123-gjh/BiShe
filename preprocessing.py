import json
import os

# 定义文件路径与分类对应关系
file_category_map = {
    "红色场馆类三元组.txt": "红色场馆类",
    "红色人物类三元组.txt": "红色人物类",
    "历史事件类三元组.txt": "历史事件类",
    "红色展品类三元组.txt": "红色展品类",
    "旅游服务类三元组.txt": "旅游服务类"
}

# 存储所有预处理后的数据
all_data = []

# 批量读取并处理文件
for file_name, category in file_category_map.items():
    with open(file_name, "r", encoding="utf-8") as f:
        lines = f.readlines()
        # 标记当前数据类型（实体-关系-实体/实体-属性-属性值）
        current_data_type = ""
        for line in lines:
            line = line.strip()
            # 识别数据类型标题
            if "（一）实体 - 关系 - 实体" in line:
                current_data_type = "实体-关系-实体"
                continue
            elif "（二）实体 - 属性 - 属性值" in line:
                current_data_type = "实体-属性-属性值"
                continue
            # 处理三元组数据（跳过空行与标题行）
            if line and "-" in line and current_data_type:
                if current_data_type == "实体-关系-实体":
                    parts = line.split(" - ")
                    if len(parts) == 3:
                        all_data.append({
                            "分类": category,
                            "数据类型": current_data_type,
                            "主体": parts[0].strip(),
                            "关系": parts[1].strip(),
                            "客体": parts[2].strip()
                        })
                else:
                    parts = line.split(" - ")
                    if len(parts) == 3:
                        all_data.append({
                            "分类": category,
                            "数据类型": current_data_type,
                            "主体": parts[0].strip(),
                            "属性": parts[1].strip(),
                            "属性值": parts[2].strip()
                        })

# 保存为JSON文件（API输入数据）
with open("大连红色旅游三元组_预处理.json", "w", encoding="utf-8") as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f"预处理完成，共生成{len(all_data)}条三元组数据，已保存至大连红色旅游三元组_预处理.json")