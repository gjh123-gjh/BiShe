"""
详细的网络诊断工具 - 检查防火墙、代理、DNS 等问题
"""
import os
import sys
import subprocess
import socket
from pathlib import Path

def run_cmd(cmd, description=""):
    """运行命令并捕获输出"""
    if description:
        print(f"\n【{description}】")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timeout", -1
    except Exception as e:
        return "", str(e), -1

print("=" * 80)
print("🔧 详细网络诊断工具")
print("=" * 80)

# 1. Windows 防火墙状态
print("\n【1】Windows 防火墙状态")
print("-" * 80)
stdout, stderr, code = run_cmd(
    ["powershell", "-Command", "Get-NetFirewallProfile | Select-Object Name, Enabled"],
    "检查防火墙状态"
)
if code == 0:
    print(stdout)
else:
    print(f"✗ 无法读取防火墙状态: {stderr}")

# 2. 检查 Python 是否被防火墙允许
print("\n【2】Python 应用防火墙规则")
print("-" * 80)
python_exe = sys.executable
print(f"Python 可执行文件: {python_exe}")
stdout, stderr, code = run_cmd(
    ["powershell", "-Command", f'Get-NetFirewallApplicationFilter -Program "{python_exe}" -ErrorAction SilentlyContinue | Select-Object Program'],
    "检查 Python 防火墙规则"
)
if code == 0 and stdout.strip():
    print("✓ 已为 Python 配置防火墙规则:")
    print(stdout)
else:
    print("⚠ 未找到 Python 的防火墙规则")
    print("  建议: 检查 Windows 安全中心 → 防火墙与网络保护 → 允许应用通过防火墙")

# 3. 代理配置检查
print("\n【3】Windows 代理配置")
print("-" * 80)
stdout, stderr, code = run_cmd(
    ["netsh", "winhttp", "show", "proxy"],
    "检查 winhttp 代理设置"
)
if code == 0:
    lines = stdout.strip().split('\n')
    for line in lines:
        if line.strip():
            print(f"  {line}")
else:
    print(f"⚠ 无法读取代理配置")

# 4. 环境变量检查
print("\n【4】环境变量")
print("-" * 80)
proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "NO_PROXY"]
for var in proxy_vars:
    value = os.environ.get(var)
    if value:
        print(f"  {var}: {value}")
if not any(os.environ.get(v) for v in proxy_vars):
    print("  （未设置代理环境变量）")

# 5. DNS 测试
print("\n【5】DNS 测试")
print("-" * 80)

dns_tests = [
    ("api.openai.com", "OpenAI API"),
    ("api.deepseek.ai", "DeepSeek API"),
    ("8.8.8.8", "Google DNS"),
]

for host, name in dns_tests:
    try:
        ip = socket.gethostbyname(host)
        print(f"  ✓ {name:20} ({host:20}) -> {ip}")
    except socket.gaierror as e:
        print(f"  ✗ {name:20} ({host:20}) -> DNS 解析失败: {e}")
    except Exception as e:
        print(f"  ✗ {name:20} ({host:20}) -> 错误: {e}")

# 6. 网络连接测试（使用 Python requests）
print("\n【6】使用 Python requests 测试连接")
print("-" * 80)
try:
    import requests
    
    test_urls = [
        ("https://api.openai.com/v1/models", "OpenAI API"),
        ("https://api.deepseek.ai/v1/models", "DeepSeek API"),
        ("https://www.google.com", "Google（公共测试）"),
    ]
    
    for url, name in test_urls:
        try:
            print(f"\n  测试 {name}: {url}")
            resp = requests.head(url, timeout=5, verify=False)
            print(f"    ✓ 连接成功 (HTTP {resp.status_code})")
        except requests.exceptions.ProxyError as e:
            print(f"    ✗ 代理错误: {str(e)[:100]}")
        except requests.exceptions.ConnectionError as e:
            print(f"    ✗ 连接失败 (DNS/防火墙): {str(e)[:100]}")
        except requests.exceptions.Timeout:
            print(f"    ✗ 连接超时 (防火墙可能阻止)")
        except requests.exceptions.SSLError as e:
            print(f"    ⚠ SSL 错误: {str(e)[:100]}")
        except Exception as e:
            print(f"    ✗ {type(e).__name__}: {str(e)[:100]}")
except ImportError:
    print("  ✗ requests 库未安装")

# 7. tracert 测试（追踪路由）
print("\n【7】追踪网络路由（tracert）")
print("-" * 80)
print("  正在追踪到 api.openai.com 的路由...")
stdout, stderr, code = run_cmd(
    ["tracert", "-h", "8", "api.openai.com"],
    ""
)
if code == 0:
    lines = stdout.strip().split('\n')[:5]  # 只显示前5行
    for line in lines:
        if line.strip():
            print(f"    {line}")
else:
    print(f"  ✗ tracert 失败（可能权限不足）")

# 8. 建议
print("\n" + "=" * 80)
print("🔧 诊断建议")
print("=" * 80)

print("\n根据诊断结果，请按以下顺序尝试：")
print()
print("【方案 1】添加 Python 到防火墙白名单（最可能的原因）")
print("  1. 打开 Windows 安全中心")
print("  2. 进入「防火墙与网络保护」")
print("  3. 点击「允许应用通过防火墙」")
print("  4. 点击「更改设置」（需要管理员权限）")
print("  5. 找到 Python 应用，确保「私有」和「公用」都勾选")
print("  6. 点击「确定」保存")
print()
print("【方案 2】重置 Windows 代理配置")
print("  在 PowerShell（管理员）中运行：")
print("  > netsh winhttp reset proxy")
print("  > ipconfig /flushdns")
print()
print("【方案 3】配置代理（如果你的网络需要代理）")
print("  在 PowerShell（管理员）中运行：")
print("  > netsh winhttp set proxy proxy-server=\"http://proxy.example.com:8080\"")
print("  （请替换为你实际的代理地址）")
print()
print("【方案 4】尝试使用 VPN")
print("  某些地区或ISP可能限制了对这些API的访问")
print()

print("=" * 80)
print("✅ 诊断完成。请尝试上述解决方案后重新运行 qa_pipeline.py")
print("=" * 80)
