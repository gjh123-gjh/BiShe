import requests
from lxml import html
import re
import json
import csv
import os

# 配置 Headers 防爬虫
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}

def crawl_bendibao(url):
    """
    抓取大连本地宝内容
    """
    print(f"正在爬取大连本地宝: {url}")
    try:
        response = requests.get(url, headers=HEADERS)
        response.encoding = 'utf-8' # 本地宝有时需要手动设为 utf-8
        if response.status_code != 200:
            print(f"请求失败: {response.status_code}")
            return None
        
        tree = html.fromstring(response.text)
        
        # 提取标题
        title = tree.xpath('//div[@class="top-title"]/text()')
        title = title[0].strip() if title else "未知标题"
        
        # 提取正文 (所有段落文本)
        content_list = tree.xpath('//div[contains(@class, "article-content")]//p//text()')
        content = "\n".join([c.strip() for c in content_list if c.strip()])
        
        return {
            "source": "大连本地宝",
            "url": url,
            "title": title,
            "content": content
        }
    except Exception as e:
        print(f"爬取本地宝出错: {e}")
        return None

def crawl_tencent(url):
    """
    抓取腾讯新闻内容 (处理 JS 动态嵌入数据)
    """
    print(f"正在爬取腾讯新闻: {url}")
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"请求失败: {response.status_code}")
            return None
        
        # 腾讯新闻的正文通常在 window.DATA 脚本中
        # 使用正则提取 JSON 内容
        match = re.search(r'window\.DATA\s*=\s*({.*?});', response.text, re.DOTALL)
        if not match:
            print("未能找到 window.DATA 脚本内容")
            return None
        
        data_json = json.loads(match.group(1))
        
        # 提取标题
        title = data_json.get("title", "未知标题")
        
        # 提取 HTML 字符串内容
        html_str = data_json.get("originContent", {}).get("text", "")
        if not html_str:
            print("未能提取到正文 HTML")
            return None
        
        # 对解码后的 HTML 进行二次 XPath 解析
        inner_tree = html.fromstring(html_str)
        # 按照用户要求的 XPath: //section[@data-autoskip="1"]
        sections = inner_tree.xpath('//section[@data-autoskip="1"]')
        
        content_parts = []
        for section in sections:
            # 提取该 section 下的所有文本内容
            text = section.xpath('.//text()')
            if text:
                content_parts.append("".join([t.strip() for t in text if t.strip()]))
        
        content = "\n".join(content_parts)
        
        return {
            "source": "腾讯新闻",
            "url": url,
            "title": title,
            "content": content
        }
    except Exception as e:
        print(f"爬取腾讯新闻出错: {e}")
        return None

def save_to_csv(data_list, filename="red_tourism_data.csv"):
    """
    保存结果到 CSV
    """
    if not data_list:
        print("没有可保存的数据")
        return
    
    keys = data_list[0].keys()
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        if not file_exists:
            dict_writer.writeheader()
        dict_writer.writerows(data_list)
    print(f"数据已成功保存至: {filename}")

if __name__ == "__main__":
    bendibao_url = "https://dl.bendibao.com/tour/202071/61801.shtm"
    tencent_url = "https://news.qq.com/rain/a/20250903A08IG400"
    
    results = []
    
    # 分开调用
    data_bd = crawl_bendibao(bendibao_url)
    if data_bd:
        results.append(data_bd)
        
    data_tx = crawl_tencent(tencent_url)
    if data_tx:
        results.append(data_tx)
        
    # 保存数据
    if results:
        save_to_csv(results)
        print("\n爬取完成！已提取内容摘要：")
        for item in results:
            print(f"[{item['source']}] 标题: {item['title']} (内容长度: {len(item['content'])})")
