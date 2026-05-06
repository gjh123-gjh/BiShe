import requests
from lxml import html
import re
import json
import csv
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================= 配置区 =================
# 目标搜索 URL
SEARCH_URL = "https://news.qq.com/search?query=%E5%A4%A7%E8%BF%9E%E6%8A%97%E6%88%98%E8%8B%B1%E9%9B%84%E4%BA%BA%E7%89%A9%E8%B0%B1&total=39&page=1"
# 搜索结果中文章卡片的 XPath
XPATH_ARTICLE_LINKS = '//div[@class="card-margin img-text-card"]//a'
# 数据保存路径
OUTPUT_CSV = r"d:\BiShe\scripts\red_tourism_data.csv"
# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}

def init_driver():
    """
    初始化 Selenium 浏览器驱动 (无头模式)
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 开启无头模式
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_search_results_links(driver, url):
    """
    使用 Selenium 访问搜索结果页并提取文章链接
    """
    print(f"正在访问搜索页面: {url}")
    driver.get(url)
    
    links = []
    try:
        # 等待文章卡片加载出来
        wait = WebDriverWait(driver, 15)
        elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, XPATH_ARTICLE_LINKS)))
        
        for elem in elements:
            href = elem.get_attribute("href")
            if href and href not in links:
                links.append(href)
        
        print(f"提取到 {len(links)} 个文章链接")
    except Exception as e:
        print(f"提取链接失败: {e}")
    
    return links

def crawl_tencent_article(url):
    """
    抓取腾讯新闻文章详情 (解析 window.DATA)
    """
    print(f"正在抓取详情页: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"详情页请求失败: {response.status_code}")
            return None
        
        # 提取 window.DATA
        match = re.search(r'window\.DATA\s*=\s*({.*?});', response.text, re.DOTALL)
        if not match:
            print("未能找到 window.DATA 数据结构")
            return None
        
        data_json = json.loads(match.group(1))
        title = data_json.get("title", "未知标题")
        
        # 提取内容 HTML 并解析文本
        html_str = data_json.get("originContent", {}).get("text", "")
        if not html_str:
            print("正文 HTML 为空")
            return None
            
        inner_tree = html.fromstring(html_str)
        # 支持多种内容容器 XPath，优先使用用户提到的 section[@data-autoskip="1"]
        content_parts = inner_tree.xpath('//section[@data-autoskip="1"]//text() | //p//text()')
        content = "\n".join([c.strip() for c in content_parts if c.strip()])
        
        return {
            "source": "腾讯新闻",
            "url": url,
            "title": title,
            "content": content
        }
    except Exception as e:
        print(f"抓取详情页出错: {e}")
        return None

def save_to_csv(data_list, filename):
    """
    将结果追加保存到 CSV
    """
    if not data_list:
        return
    
    keys = data_list[0].keys()
    file_exists = os.path.isfile(filename)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        if not file_exists:
            dict_writer.writeheader()
        dict_writer.writerows(data_list)
    print(f"数据已追加保存至: {filename}")

def main():
    driver = None
    try:
        # 1. 初始化驱动
        driver = init_driver()
        
        # 2. 获取所有搜索结果链接
        links = get_search_results_links(driver, SEARCH_URL)
        
        if not links:
            print("没有找到任何链接，退出。")
            return
            
        # 3. 遍历链接爬取详情
        all_results = []
        for index, link in enumerate(links):
            print(f"进度: {index+1}/{len(links)}")
            article_data = crawl_tencent_article(link)
            if article_data:
                all_results.append(article_data)
            time.sleep(1) # 适当延时，保护服务器
            
        # 4. 保存数据
        if all_results:
            save_to_csv(all_results, OUTPUT_CSV)
            print(f"\n任务完成！成功爬取并保存了 {len(all_results)} 篇文章。")
        else:
            print("未能提取到有效文章内容。")
            
    except Exception as e:
        print(f"主程序运行出错: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
