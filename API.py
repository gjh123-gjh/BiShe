import requests
import json
import re

API_KEY = "sk-99f0e543eb9945fb9c43b07d8bbfc864"
API_URL = "https://api.deepseek.com/v1/chat/completions"

# 读取预处理数据
with open("test.json", "r", encoding="utf-8") as f:
    preprocessed_data = json.load(f)

# 构造Prompt（强调禁止重复转义）
prompt = f"""
返回JSON数组时，确保：
1. 键和值用双引号包裹，且双引号前无反斜杠（正确："分类": "红色场馆类"，错误："分类\": "红色场馆类\"）；
2. 无多余空格和引号；
3. 数组最后一个对象后无逗号。

数据：{json.dumps(preprocessed_data[:10], ensure_ascii=False)}  # 先小批量测试
"""

# 发送请求
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
payload = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.1
}

response = requests.post(API_URL, json=payload, headers=headers)
response_data = response.json()
extracted_content = response_data["choices"][0]["message"]["content"]

# 基础清洗（去除Markdown标记）
json_str = re.sub(r'^```json\s*', '', extracted_content)
json_str = re.sub(r'\s*```$', '', json_str).strip()

# 核心修复：移除双引号前的多余反斜杠
json_str = re.sub(r'\\"', '"', json_str)

# 修复其他可能的格式问题（多余逗号、空格）
json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # 移除末尾多余逗号
json_str = re.sub(r'\s+', ' ', json_str)  # 合并多余空格

# 解析
try:
    extracted_data = json.loads(json_str)
    print("解析成功，数据量：", len(extracted_data))
    # 保存结果
    with open("test1.json", "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=2)
except json.JSONDecodeError as e:
    start = max(0, e.pos - 50)
    end = min(len(json_str), e.pos + 50)
    print(f"错误位置：{e.pos}，上下文：{json_str[start:end]}")
    print("修复后内容：", json_str)