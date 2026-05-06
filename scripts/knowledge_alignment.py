import csv
import os
import re
from collections import defaultdict

# 噪声黑名单：完全无用的提取词
BLACKLIST = {
    "位革命", "由于家贫", "并在大关家村", "年将", "念英雄", "大连市", "苏军", "由于", "并在", "年考", "从普", "从此", "展示了", "现设置", "迹展览有", "该馆是", "生动展示了", "市文化和", "他们是", "展现他为", "同贺龙", "当选为", "暨世界", "从此投身", "从湖南", "在长期", "追寻", "党员李", "在此生活"
}

# 冗余前缀：需要从实体名称开头删减的内容
JUNK_PREFIXES = [
    "为纪念", "在中国人民", "中苏两国人民在抗击", "6年领导的", "市文化和旅游局带您走进大连这些", "迹展览有", "一楼设有", "在大连", "及其", "并在", "旨在", "开始", "通过", "现设", "展现", "通过", "包括"
]

# 场馆核心后缀
VENUE_KEYWORDS = ["纪念馆", "旧址", "故居", "博物馆", "陵园", "纪念塔", "胜利塔", "展室", "文史馆", "公园", "指挥所", "窑洞", "珍藏馆"]

def clean_entity_name(name, e_type):
    """
    精简实体名称，去除句子前缀等
    """
    # 1. 移除干扰前缀
    for prefix in JUNK_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
    
    # 2. 针对场馆进行核心词提取
    if e_type == "红色场馆":
        # 移除句子式的动词
        name = re.split(r'建立|敬立|设有|迁移至', name)[-1]
        # 如果名称中包含“的”，通常前面是修饰语，取后面（例如：旅顺口区的旅顺博物馆）
        # 但要注意不要误删，这里仅处理明显过长的
        if len(name) > 10 and "的" in name:
            name = name.split("的")[-1]
            
    # 3. 针对事件进行核心提取
    if e_type == "历史事件":
        if "中的" in name: name = name.split("中的")[-1]
        name = name.lstrip("“").rstrip("”")

    return name.strip(" ,，。、")

def align_entities(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"错误: 找不到输入文件 {input_file}")
        return

    # 1. 初始读取与过滤
    temp_entities = []
    with open(input_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['entity_name']
            e_type = row['entity_type']
            freq = int(row['frequency'])
            
            # 过滤黑名单和过短字符
            if name in BLACKLIST or len(name) < 2:
                continue
            
            # 初步精简
            clean_name = clean_entity_name(name, e_type)
            if len(clean_name) < 2: continue
            
            temp_entities.append({"name": clean_name, "type": e_type, "freq": freq})

    # 2. 归一化字典 (key: 标准名, value: 频次)
    final_entities = defaultdict(lambda: {"type": "", "freq": 0})

    # 按长度降序排列，大的先进入字典，小的如果在大里面则归并
    temp_entities.sort(key=lambda x: len(x['name']), reverse=True)

    names_list = [] # 用于子串查找

    for item in temp_entities:
        name = item['name']
        e_type = item['type']
        freq = item['freq']
        
        merged = False
        # 检查是否已存在一个更长且包含此名字的同类型实体
        for standard_name in names_list:
            if name in standard_name and final_entities[standard_name]["type"] == e_type:
                final_entities[standard_name]["freq"] += freq
                merged = True
                break
        
        if not merged:
            if name not in final_entities:
                final_entities[name] = {"type": e_type, "freq": freq}
                names_list.append(name)
            else:
                final_entities[name]["freq"] += freq

    # 3. 结果排序并输出
    results = []
    for name, info in final_entities.items():
        results.append({
            "entity_name": name,
            "entity_type": info["type"],
            "frequency": info["freq"]
        })
    
    # 按频次降序
    results.sort(key=lambda x: x['frequency'], reverse=True)

    with open(output_file, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["entity_name", "entity_type", "frequency"])
        writer.writeheader()
        writer.writerows(results)

    print(f"对齐完成！实体数从 {len(temp_entities)} 优化至 {len(results)}。")
    print(f"最终结果已保存至: {output_file}")

if __name__ == "__main__":
    input_csv = "extracted_entities.csv"
    output_csv = "aligned_entities.csv"
    align_entities(input_csv, output_csv)
    
    # 打印前10个精简后的实体
    if os.path.exists(output_csv):
        print("\n对齐后的实体预览 (前10个):")
        with open(output_csv, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                if count < 10:
                    print(f"- [{row['entity_type']}] {row['entity_name']} (权重: {row['frequency']})")
                    count += 1
