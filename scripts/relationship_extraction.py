import csv
import re
import os

def load_entities(entity_file):
    """
    加载实体字典，格式: {name: type}
    """
    entities = {}
    if not os.path.exists(entity_file):
        return entities
    with open(entity_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entities[row['entity_name']] = row['entity_type']
    return entities

def extract_relationships(text_file, entity_dict, output_file):
    """
    关系抽取主逻辑
    """
    relationships = []
    
    if not os.path.exists(text_file):
        print(f"错误: 找不到文件 {text_file}")
        return

    # 预定义的谓词识别正则
    patterns = {
        "BORN_IN": r"出生于|生于|原籍",
        "LOCATED_IN": r"位于|地址：|坐落在|地址",
        "PARTICIPATED_IN": r"参加|参加了|领导了|投身|创建了|开始|参与",
        "COLLEAGUE": r"战友|同(.*)等创建|同(.*)率部|送了挽联",
        "COMMEMORATES": r"纪念馆|纪念|安葬|再现了",
        "OFFICE": r"任|担任|一任厂长|任政委"
    }

    with open(text_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            content = row['content']
            # 将正文按句号、分号、问号切分，降低干扰
            sentences = re.split(r'[。；！？\n]', content)
            
            for sent in sentences:
                sent = sent.strip()
                if not sent: continue

                # 在句子中识别已存在的实体
                found_entities = []
                for name, e_type in entity_dict.items():
                    if name in sent:
                        found_entities.append((name, e_type))
                
                if len(found_entities) < 2:
                    # 如果只有一个实体，可以尝试寻找属性（如地址）
                    if len(found_entities) == 1:
                        name, e_type = found_entities[0]
                        if e_type == "红色场馆" or e_type == "红色人物":
                            match = re.search(r'(?:地址|位于|安葬于)[：\s]*([^，。；\s]{2,20})', sent)
                            if match:
                                relationships.append((name, "位于", match.group(1)))
                    continue

                # 多个实体共现时，根据谓词判定关系
                for i in range(len(found_entities)):
                    for j in range(i + 1, len(found_entities)):
                        ent1, type1 = found_entities[i]
                        ent2, type2 = found_entities[j]
                        
                        # 同一句子中两个实体的相对位置
                        # 简单的逻辑：谁在前谁是 Head
                        
                        # 示例规则 1: 人物 - 战友 - 人物
                        if type1 == "红色人物" and type2 == "红色人物":
                            if re.search(r'战友|同事|同|联合', sent):
                                relationships.append((ent1, "战友/关联", ent2))
                        
                        # 示例规则 2: 人物 - 参与 - 事件
                        if type1 == "红色人物" and type2 == "历史事件":
                            if re.search(patterns["PARTICIPATED_IN"], sent):
                                relationships.append((ent1, "参与", ent2))
                        
                        # 示例规则 3: 场馆 - 纪念 - 人物
                        if type1 == "红色场馆" and type2 == "红色人物":
                            if re.search(patterns["COMMEMORATES"], sent):
                                relationships.append((type1, "纪念", type2)) # 这里应保留实体名
                                relationships.append((ent1, "纪念/展示", ent2))
                                
                        # 示例规则 4: 场馆 - 位于 - 地址 (如果 ent2 恰好是包含地址特征的实体)
                        if type1 == "红色场馆" and "街道" in ent2 or "区" in ent2:
                            relationships.append((ent1, "位于", ent2))

    # 去重处理
    unique_rels = list(set(relationships))
    
    # 写入 CSV
    with open(output_file, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["head", "relation", "tail"])
        for rel in unique_rels:
            writer.writerow(rel)
    
    print(f"抽取完成！共生成 {len(unique_rels)} 条三元组关系。")
    print(f"结果已保存至: {output_file}")

if __name__ == "__main__":
    entities = load_entities("aligned_entities.csv")
    input_text = "red_tourism_cleaned.csv"
    output_rels = "relationships.csv"
    
    extract_relationships(input_text, entities, output_rels)

    # 预览结果
    if os.path.exists(output_rels):
        print("\n三元组关系预览 (前15条):")
        with open(output_rels, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                if count < 15:
                    print(f"- {row['head']} --({row['relation']})--> {row['tail']}")
                    count += 1
