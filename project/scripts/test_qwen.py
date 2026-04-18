#!/usr/bin/env python3
"""
Quick test script to verify qwen3-max availability using the openai SDK.
Reads API key from APP_OPENAI_API_KEY, APP_DASHSCOPE_API_KEY or OPENAI_API_KEY.
"""
from dotenv import load_dotenv
load_dotenv()  # 会把项目根的 .env 加入 os.environ
import os
import sys

try:
    from openai import OpenAI
except Exception as e:
    print("openai SDK not installed:", e)
    sys.exit(2)

key = os.getenv("APP_OPENAI_API_KEY") or os.getenv("APP_DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
if not key:
    print("NO API KEY: set APP_OPENAI_API_KEY or OPENAI_API_KEY in env or .env")
    sys.exit(2)

client = OpenAI(
    api_key=key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

messages = [
    {"role": "user", "content": "用儿童能懂的方式解释\"电\"是什么。简短回答，适合 15 岁儿童和青少年。"}
]

print("Calling qwen3-max...")
try:
    resp = client.chat.completions.create(
        model="qwen3-max",
        messages=messages,
        temperature=0.2,
        max_tokens=200,  # 可选，避免过长
    )

    # 标准 OpenAI 响应结构
    content = resp.choices[0].message.content

    print('--- RESPONSE START ---')
    if content:
        print(content.strip())
    else:
        print('No content in response; full response:')
        print(resp.model_dump_json(indent=2))
    print('--- RESPONSE END ---')
    sys.exit(0)

except Exception as e:
    print('Request failed:', repr(e))
    sys.exit(3)