"""
诊断脚本：检查 API Key、环境变量加载和网络连接。
"""
import os
import sys

# 尝试加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ python-dotenv 已加载 .env 文件")
except ImportError:
    print("⚠ python-dotenv 未安装，直接从环境变量读取")

# 检查 API Key
openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()

print("\n=== API Key 检查 ===")
print(f"OPENAI_API_KEY: {'配置' if openai_key else '未配置'} (前16字: {openai_key[:16]}...)" if openai_key else "未配置")
print(f"DEEPSEEK_API_KEY: {'配置' if deepseek_key else '未配置'} (前16字: {deepseek_key[:16]}...)" if deepseek_key else "未配置")

print("\n=== 模型配置 ===")
print(f"OPENAI_MODEL: {os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')}") 
print(f"DEEPSEEK_BASE_URL: {os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.ai/v1')}")

# 测试 requests 连接
print("\n=== 网络连接测试 ===")
try:
    import requests
    print("✓ requests 库已安装")
    
    # 尝试 DNS 解析
    try:
        import socket
        ip = socket.gethostbyname("api.deepseek.ai")
        print(f"✓ DNS 解析成功: api.deepseek.ai -> {ip}")
    except Exception as e:
        print(f"✗ DNS 解析失败: {e}")
    
    # 尝试 HTTPS 连接（不发送实际请求）
    try:
        resp = requests.head("https://api.openai.com", timeout=5)
        print(f"✓ OpenAI 服务器连接成功 (HTTP {resp.status_code})")
    except requests.exceptions.ProxyError as e:
        print(f"✗ 代理错误: {e}")
        print("   建议: 检查系统代理设置或禁用代理")
    except Exception as e:
        print(f"⚠ OpenAI 连接测试: {type(e).__name__}: {e}")
        
except ImportError:
    print("✗ requests 库未安装")

# 测试 OpenAI 库
print("\n=== OpenAI 库测试 ===")
try:
    import openai
    print("✓ openai 库已安装")
    openai.api_key = openai_key
    if openai_key:
        print("  已设置 API Key")
    else:
        print("  ⚠ 未设置 API Key，运行会失败")
except ImportError:
    print("✗ openai 库未安装")

# 测试 DeepSeek 客户端
print("\n=== DeepSeek 客户端测试 ===")
try:
    from deepseek_client import DeepSeekClient
    print("✓ DeepSeekClient 导入成功")
    client = DeepSeekClient()
    print(f"  API Key 状态: {'配置' if client.api_key else '未配置'}")
    print(f"  Base URL: {client.base_url}")
except Exception as e:
    print(f"✗ DeepSeekClient 导入失败: {e}")

print("\n=== 建议 ===")
if not openai_key or not deepseek_key:
    print("1. 请在 .env 文件中填入正确的 API Key")
elif "ProxyError" in str(sys.exc_info()):
    print("1. 系统代理配置有问题，请尝试:")
    print("   - 检查 Windows 代理设置")
    print("   - 或禁用代理: set HTTP_PROXY= && set HTTPS_PROXY=")
else:
    print("所有检查通过，可以运行 qa_pipeline.py")
