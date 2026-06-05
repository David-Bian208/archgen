#!/usr/bin/env python3
"""ArchGen DeepSeek API 配置测试"""

import sys
import yaml
from pathlib import Path

# 加载配置
config_path = Path(__file__).parent / "config" / "config.yaml"
with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

api_key = config["llm"]["api_key"]
base_url = config["llm"]["base_url"]
model = config["llm"]["model"]

print("=" * 60)
print("ArchGen DeepSeek API 配置测试")
print("=" * 60)
print(f"\nAPI Key: {api_key[:10]}...{api_key[-6:]}")
print(f"Base URL: {base_url}")
print(f"Model: {model}")
print(f"Timeout: {config['llm']['timeout']}s")
print(f"Max Tokens: {config['llm']['max_tokens']}")

# 测试 API 调用
print("\n正在测试 API 调用...")

import httpx

test_prompt = "你是一个测试助手。请只回复'OK'两个字符。"

try:
    response = httpx.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": test_prompt}],
            "max_tokens": 50,
            "temperature": 0.1
        },
        timeout=config["llm"]["timeout"]
    )
    
    if response.status_code == 200:
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        print(f"\n✅ API 调用成功！")
        print(f"回复内容：{reply}")
        print(f"Token 使用：prompt={result['usage']['prompt_tokens']}, completion={result['usage']['completion_tokens']}")
    else:
        print(f"\n❌ API 调用失败！")
        print(f"状态码：{response.status_code}")
        print(f"响应：{response.text}")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ 测试出错：{e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("配置验证完成！可以启动服务了。")
print("=" * 60)
