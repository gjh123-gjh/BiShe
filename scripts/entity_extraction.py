import csv
import re
import os
from collections import Counter

# 预定义的红色人物库 (基于语料库初步提取)
RED_FIGURES_DB = {
    "关向应", "蔡和森", "邓中夏", "周恩来", "毛泽东", "贺龙", "任弼时", 
    "刘伯承", "焦裕禄", "张有萱", "吴屏周", "史春英", "李震瀛", "朱德", 
    "宋庆龄", "彭德怀", "穆军", "侯智良"
}

# 场馆核心后缀
VENUE_SUFFIXES = r"纪念馆|旧址|故居|博物馆|陵园|纪念塔|胜利塔|展室|文史馆|公园|指挥所|窑洞|珍藏馆"

# 历史事件核心关键词
EVENT_KEYWORDS = r"战争|长征|罢工|惨案|突围|起义|会师|建党|革命"

def extract_figures(text):
    """提取人物实体"""
    found = []
    for name in RED_FIGURES_DB:
        if name in text:
            found.append(name)
    # 额外规则：匹配 "XX同志" 或 "XX烈士"
    extra = re.findall(r'([\u4e00-\u9fa5]{2,3})(?:同志|烈士|先驱)', text)
    return list(set(found + extra))

def extract_venues(text):
    """提取红色场馆实体"""
    # 匹配前面的修饰词+核心后缀，例如 "大连中华工学会旧址"
    # 规则：匹配2-15个汉字，以预定义后缀结尾
    pattern = rf'([\u4e00-\u9fa5]{{2,15}}(?:{VENUE_SUFFIXES}))'
    matches = re.findall(pattern, text)
    # 进一步清洗：去除过短或明显的噪声
    return list(set([m for m in matches if len(m) > 3]))

def extract_events(text):
    """提取历史事件实体"""
    # 匹配包含特定关键词的短语，如 "四二七“福纺”工人大罢工"
    # 或者通用的 "抗日战争", "长征"
    events = []
    # 1. 精确匹配长事件名 (可能有引号)
    long_events = re.findall(r'([^，。；\s]{2,15}(?:' + EVENT_KEYWORDS + r'))', text)
    events.extend(long_events)
    
    # 2. 检查特定已知大事件
    known_events = ["抗日战争", "长征", "解放战争", "抗美援朝", "世界反法西斯战争", "五卅惨案"]
    for ke in known_events:
        if ke in text:
            events.append(ke)
            
    return list(set(events))

def process_extraction(input_file, output_file):
    """
    执行知识抽取逻辑
    """
    print(f"正在从 {input_file} 抽取实体...")
    
    if not os.path.exists(input_file):
        print(f"错误: 找不到文件 {input_file}")
        return

    all_entities = [] # 存储结果 [(name, type), ...]

    with open(input_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            content = row['content']
            
            # 抽取各类实体
            figs = extract_figures(content)
            for f_name in figs:
                all_entities.append((f_name, "红色人物"))
                
            vens = extract_venues(content)
            for v_name in vens:
                all_entities.append((v_name, "红色场馆"))
                
            evts = extract_events(content)
            for e_name in evts:
                all_entities.append((e_name, "历史事件"))

    # 统计词频并去重
    entity_counts = Counter(all_entities)
    
    # 构建最终列表
    sorted_entities = []
    for (name, e_type), freq in entity_counts.most_common():
        sorted_entities.append({
            "entity_name": name,
            "entity_type": e_type,
            "frequency": freq
        })

    # 写入 CSV
    fieldnames = ["entity_name", "entity_type", "frequency"]
    with open(output_file, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_entities)
    
    print(f"抽取完成！共找到 {len(sorted_entities)} 个唯一实体。")
    print(f"结果已保存至: {output_file}")

if __name__ == "__main__":
    input_csv = "red_tourism_cleaned.csv"
    output_csv = "extracted_entities.csv"
    process_extraction(input_csv, output_csv)
    
    # 打印部分结果展示
    print("\n实体抽取预览 (前15个):")
    if os.path.exists(output_csv):
        with open(output_csv, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                if count < 15:
                    print(f"- [{row['entity_type']}] {row['entity_name']} (频次: {row['frequency']})")
                    count += 1
