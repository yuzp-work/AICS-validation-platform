#!/usr/bin/env python3
"""
本地调试脚本 - 测试 strands agent retrieve 工具的返回结构

使用方法:
1. 确保已激活 venv: cd lambda && source .venv/bin/activate
2. 运行: python debug_retrieve.py
"""

import os
import json

# 配置
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "SWOFQ7S45C")
MODEL_ID = os.environ.get("MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0")
AWS_REGION = "us-west-2"

# 关键：设置 AWS 区域环境变量，确保 retrieve 工具使用正确的区域
os.environ["AWS_REGION"] = AWS_REGION
os.environ["AWS_DEFAULT_REGION"] = AWS_REGION

# 设置环境变量供 retrieve 工具使用
os.environ["KNOWLEDGE_BASE_ID"] = KNOWLEDGE_BASE_ID

from strands import Agent
from strands.models import BedrockModel
from strands_tools import retrieve

def print_json(obj, indent=2):
    """安全打印 JSON"""
    try:
        print(json.dumps(obj, indent=indent, ensure_ascii=False, default=str))
    except:
        print(obj)

def main():
    print(f"=== Strands Agent Retrieve 调试 ===")
    print(f"Knowledge Base ID: {KNOWLEDGE_BASE_ID}")
    print(f"Model ID: {MODEL_ID}")
    print(f"AWS Region: {AWS_REGION}")
    print()
    
    # 初始化模型
    model = BedrockModel(
        model_id=MODEL_ID,
        region=AWS_REGION,
        max_tokens=4096,
        temperature=0.3
    )
    
    # 初始化 Agent
    agent = Agent(
        model=model,
        system_prompt="你是一个专业的客服助手。请根据提供的知识库内容回答用户的问题。",
        tools=[retrieve]
    )
    
    # 测试问题
    question = "如何修改昵称"
    print(f"问题: {question}")
    print()
    
    # 调用 agent
    print("正在调用 agent...")
    response = agent(question)
    print("调用完成!")
    print()
    
    # 打印 agent.messages 的完整结构
    print("=" * 60)
    print("=== agent.messages 完整结构 ===")
    print("=" * 60)
    messages = agent.messages
    print(f"消息数量: {len(messages)}")
    print()
    
    for i, msg in enumerate(messages):
        print(f"{'='*50}")
        print(f"Message {i}")
        print(f"{'='*50}")
        
        if isinstance(msg, dict):
            print(f"Type: dict")
            print(f"Keys: {list(msg.keys())}")
            print(f"Role: {msg.get('role', 'N/A')}")
            
            content = msg.get('content', [])
            print(f"Content type: {type(content).__name__}")
            
            if isinstance(content, list):
                print(f"Content items: {len(content)}")
                for j, item in enumerate(content):
                    print(f"\n  --- content[{j}] ---")
                    if isinstance(item, dict):
                        print(f"  Type: dict")
                        print(f"  Keys: {list(item.keys())}")
                        
                        # 打印每个 key 的内容
                        for key in item.keys():
                            value = item[key]
                            print(f"\n  [{key}]:")
                            if isinstance(value, dict):
                                print(f"    Type: dict, Keys: {list(value.keys())}")
                                # 详细打印 toolResult
                                if key == 'toolResult':
                                    print(f"    toolUseId: {value.get('toolUseId')}")
                                    print(f"    status: {value.get('status')}")
                                    tr_content = value.get('content', [])
                                    print(f"    content type: {type(tr_content).__name__}")
                                    if isinstance(tr_content, list):
                                        print(f"    content count: {len(tr_content)}")
                                        for k, tr_item in enumerate(tr_content):
                                            print(f"\n    --- toolResult.content[{k}] ---")
                                            if isinstance(tr_item, dict):
                                                print(f"      Keys: {list(tr_item.keys())}")
                                                for tr_key in tr_item.keys():
                                                    tr_value = tr_item[tr_key]
                                                    print(f"      [{tr_key}] type: {type(tr_value).__name__}")
                                                    if isinstance(tr_value, str):
                                                        # 截断长字符串
                                                        display = tr_value[:500] + "..." if len(tr_value) > 500 else tr_value
                                                        print(f"      [{tr_key}] value: {display}")
                                                    elif isinstance(tr_value, dict):
                                                        print(f"      [{tr_key}] keys: {list(tr_value.keys())}")
                                                        # 如果是 retrievalResults，详细打印
                                                        if 'retrievalResults' in tr_value:
                                                            results = tr_value['retrievalResults']
                                                            print(f"      retrievalResults count: {len(results)}")
                                                            if results:
                                                                print(f"      First result keys: {list(results[0].keys())}")
                                                                print(f"      First result:")
                                                                print_json(results[0])
                                                        else:
                                                            print_json(tr_value)
                                                    else:
                                                        print(f"      [{tr_key}] value: {tr_value}")
                                            else:
                                                print(f"      Type: {type(tr_item).__name__}")
                                                print(f"      Value: {tr_item}")
                                # 详细打印 toolUse
                                elif key == 'toolUse':
                                    print(f"    name: {value.get('name')}")
                                    print(f"    toolUseId: {value.get('toolUseId')}")
                                    print(f"    input: {value.get('input')}")
                            elif isinstance(value, list):
                                print(f"    Type: list, Length: {len(value)}")
                            elif isinstance(value, str):
                                display = value[:200] + "..." if len(value) > 200 else value
                                print(f"    Value: {display}")
                            else:
                                print(f"    Type: {type(value).__name__}, Value: {value}")
                    else:
                        print(f"  Type: {type(item).__name__}")
                        print(f"  Value: {item}")
            else:
                print(f"Content: {content}")
        else:
            print(f"Type: {type(msg).__name__}")
            print(f"Value: {msg}")
        
        print()
    
    # 提取答案
    print("=" * 60)
    print("=== 提取的答案 ===")
    print("=" * 60)
    if hasattr(response, 'message'):
        msg = response.message
        if isinstance(msg, dict) and 'content' in msg:
            content = msg['content']
            if isinstance(content, list) and len(content) > 0:
                first = content[0]
                if isinstance(first, dict) and 'text' in first:
                    print(first['text'])

if __name__ == "__main__":
    main()
