import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

urls = {
    "bendibao": "https://dl.bendibao.com/tour/202071/61801.shtm",
    "tencent": "https://news.qq.com/rain/a/20250903A08IG400"
}

for name, url in urls.items():
    try:
        print(f"Fetching {url}...")
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        with open(f"d:/BiShe/scripts/{name}.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Saved {name}.html")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
