"""
网络调试脚本：诊断代理配置问题并尝试解决
"""
import os
import sys
import subprocess

print("=" * 70)
print("🔧 网络代理调试工具")
print("=" * 70)

# 1. 检查当前代理环境变量
print("\n【1】当前环境变量：")
for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY"]:
    value = os.environ.get(var, "（未设置）")
    print(f"  {var}: {value}")

# 2. 检查 Windows 系统代理
print("\n【2】检查 Windows 系统代理设置...")
try:
    result = subprocess.run(
        ["netsh", "winhttp", "show", "proxy"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.stdout:
        print("  " + result.stdout.replace("\n", "\n  "))
    else:
        print("  （无法读取或未设置代理）")
except Exception as e:
    print(f"  ⚠ 无法执行命令: {e}")

# 3. 解决方案
print("\n【3】推荐解决方案：")
print("\n  方案 A：禁用代理（临时）")
print("  -----")
print("  在 PowerShell 或 CMD 中运行：")
print("  ")
print("    set HTTP_PROXY=")
print("    set HTTPS_PROXY=")
print("    set NO_PROXY=*")
print("  ")
print("  然后重新运行你的脚本。")

print("\n  方案 B：重置 Windows 代理（永久）")
print("  -----")
print("  在 PowerShell（以管理员身份）运行：")
print("  ")
print("    netsh winhttp reset proxy")
print("  ")
print("  然后重启计算机或 IDE。")

print("\n  方案 C：为 Python 配置代理（如果需要代理）")
print("  -----")
print("  如果你的网络确实需要代理，修改 deepseek_client.py：")
print("  ")
print("    resp = requests.post(")
print("        url,")
print("        json=payload,")
print("        headers=self.headers,")
print("        timeout=30,")
print("        proxies={")
print("            'http': 'http://proxy.example.com:8080',")
print("            'https': 'http://proxy.example.com:8080'")
print("        }")
print("    )")

# 4. 测试连接（无代理）
print("\n【4】测试网络连接（禁用代理）...")
try:
    # 临时禁用代理
    old_http = os.environ.pop("HTTP_PROXY", None)
    old_https = os.environ.pop("HTTPS_PROXY", None)
    
    import requests
    try:
        # 测试连接（超短超时）
        resp = requests.head("https://api.deepseek.ai", timeout=3)
        print(f"  ✓ DeepSeek 服务器连接成功 (HTTP {resp.status_code})")
    except requests.exceptions.ProxyError:
        print("  ✗ 仍然是代理错误，请检查系统代理设置")
    except requests.exceptions.ConnectionError:
        print("  ✗ 无法连接 DeepSeek（可能是网络问题或 DNS）")
    except requests.exceptions.Timeout:
        print("  ✓ 网络连接正常（超时可能是服务器响应慢）")
    except Exception as e:
        print(f"  ⚠ {type(e).__name__}: {e}")
    finally:
        # 恢复代理设置
        if old_http:
            os.environ["HTTP_PROXY"] = old_http
        if old_https:
            os.environ["HTTPS_PROXY"] = old_https
except Exception as e:
    print(f"  ⚠ 测试失败: {e}")

print("\n" + "=" * 70)
print("✅ 调试完成。请按上述建议操作后重试。")
print("=" * 70)
