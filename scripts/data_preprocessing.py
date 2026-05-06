import csv
import re
import os

def clean_text(text):
    """
    清洗正文文本：去除网页噪声、多余空格和特定提示语
    """
    if not text:
        return ""
    
    # 1. 去除特定噪声提示语
    noise_patterns = [
        r'【导语】：',
        r'温馨提示：',
        r'关注微信公众号.*',
        r'大连本地宝来告诉你！',
        r'手机访问.*',
        r'点击查看.*',
        r'对话框回复.*',
        r'转载请注明.*',
        r'编辑：.*',
        r'美编：.*',
        r'校对：.*',
        r'责编：.*',
        r'主编：.*',
        r'监制：.*'
    ]
    
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)
    
    # 2. 处理多余的空白字符
    # 将多个空行替换为一个换行
    text = re.sub(r'\n\s*\n', '\n', text)
    # 去除每一行行首行尾的空格
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)
    
    return text.strip()

def preprocess_data(input_file, output_file):
    """
    读取原始 CSV，进行去重和清洗，导出结果
    """
    print(f"正在预处理数据: {input_file} -> {output_file}")
    
    if not os.path.exists(input_file):
        print(f"错误: 找不到输入文件 {input_file}")
        return

    processed_data = []
    seen_contents = set() # 用于内容去重

    with open(input_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 获取原始字段
            source = row.get('source', '')
            url = row.get('url', '')
            title = row.get('title', '').strip()
            content = row.get('content', '')
            
            # 1. 基础清洗
            cleaned_content = clean_text(content)
            
            # 2. 去重逻辑 (基于清洗后的正文内容)
            # 使用内容的哈希或特征进行判断，防止完全相同的文章重复出现
            content_fingerprint = cleaned_content[:200]  # 取前200字作为简易特征
            if not cleaned_content or content_fingerprint in seen_contents:
                continue
            
            seen_contents.add(content_fingerprint)
            
            # 3. 结果构造
            processed_row = {
                'source': source,
                'url': url,
                'title': title,
                'content': cleaned_content,
                'content_length': len(cleaned_content)
            }
            processed_data.append(processed_row)

    # 4. 写入新 CSV
    if processed_data:
        fieldnames = ['source', 'url', 'title', 'content', 'content_length']
        with open(output_file, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"预处理完成！\n原始记录数: {len(seen_contents) + (134-len(processed_data) if 'seen_contents' in locals() else 0)} (估算)\n清洗后记录数: {len(processed_data)}")
        print(f"清洗后的数据已保存至: {output_file}")
    else:
        print("警告: 清洗后没有剩余数据。")

if __name__ == "__main__":
    input_csv = "red_tourism_data.csv"
    output_csv = "red_tourism_cleaned.csv"
    preprocess_data(input_csv, output_csv)
    
    # 打印一些分析摘要
    if os.path.exists(output_csv):
        print("\n数据质量摘要：")
        with open(output_csv, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                print(f"- [{row['source']}] {row['title']} | 字数: {row['content_length']}")
