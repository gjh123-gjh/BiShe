import requests
from lxml import html
import re
import json
import csv
import os

# 配置 Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}

def crawl_specific_article(url, target_xpath):
    """
    爬取指定 URL 的内容
    """
    print(f"正在爬取: {url}")
    try:
        response = requests.get(url, headers=HEADERS, proxies={"http": None, "https": None})
        response.encoding = 'utf-8'
        if response.status_code != 200:
            print(f"请求失败: {response.status_code}")
            return None
        
        # 1. 首先尝试在原始 HTML 中直接查找
        tree = html.fromstring(response.text)
        content_nodes = tree.xpath(target_xpath)
        
        title = tree.xpath('//h1/text()') 
        title = title[0].strip() if title else "未知标题"
        
        if not content_nodes:
            # 2. 如果没找到，尝试在 window.DATA 中查找 (腾讯新闻常见模式)
            print("在原始 HTML 中未找到目标元素，尝试解析 window.DATA...")
            match = re.search(r'window\.DATA\s*=\s*({.*?});', response.text, re.DOTALL)
            if match:
                data_json = json.loads(match.group(1))
                # 提取标题
                title = data_json.get("title", title)
                # 提取正文 HTML
                html_str = data_json.get("originContent", {}).get("text", "")
                if html_str:
                    inner_tree = html.fromstring(html_str)
                    content_nodes = inner_tree.xpath(target_xpath)
        
        if not content_nodes:
            print(f"未能通过 XPath `{target_xpath}` 找到内容")
            # 备选：如果找不到用户指定的，尝试简单的正文提取逻辑
            return None
            
        # 提取并清理文本内容
        content_parts = []
        for node in content_nodes:
            # 移除 style 和 script 标签，防止提取到 CSS/JS 代码
            for tag in node.xpath('.//style | .//script'):
                tag.getparent().remove(tag)
            
            text = node.xpath('.//text()')
            if text:
                # 清理多余空白符
                cleaned_text = "\n".join([t.strip() for t in text if t.strip()])
                if cleaned_text:
                    content_parts.append(cleaned_text)
        
        content = "\n\n".join(content_parts)
        
        return {
            "url": url,
            "title": title,
            "content": content
        }
    except Exception as e:
        print(f"发生错误: {e}")
        return None

def save_to_csv(data, filename):
    """
    保存结果到 CSV
    """
    if not data:
        print("没有数据可以保存")
        return
    
    file_exists = os.path.isfile(filename)
    keys = data.keys()
    
    # 确保目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        if not file_exists:
            dict_writer.writeheader()
        dict_writer.writerow(data)
    print(f"数据已追加保存至: {filename}")

if __name__ == "__main__":
    target_url = "https://news.qq.com/rain/a/20250905A053A400"
    xpath = '//div[@class="rich_media_content"]'
    output_file = r"d:\BiShe\scripts\red_tourism_data.csv"
    
    result = crawl_specific_article(target_url, xpath)
    if result:
        save_to_csv(result, output_file)
        print(f"成功提取标题: {result['title']}")
        print(f"内容长度: {len(result['content'])}")
    else:
        print("提取失败。")
