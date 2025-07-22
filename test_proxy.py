#!/usr/bin/env python3
"""
测试Claude代理服务器的功能
"""

import asyncio
import aiohttp
import json

async def test_proxy():
    """测试代理服务器"""
import json

with open("config.json", "r") as f:
    config = json.load(f)
    base_url = config.get("proxy_url", "http://127.0.0.1:8000")
    
    async with aiohttp.ClientSession() as session:
        # 测试健康检查
        print("1. 测试健康检查...")
        async with session.get(f"{base_url}/health") as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"✓ 健康检查通过: {result}")
            else:
                print(f"✗ 健康检查失败: {resp.status}")
                return
        
        # 测试模型列表 - 默认提供商
        print("\n2. 测试默认提供商模型列表...")
        async with session.get(f"{base_url}/v1/models") as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"✓ 默认提供商模型数量: {len(result['data'])}")
                for model in result['data'][:3]:  # 只显示前3个
                    print(f"  - {model['id']} (owned_by: {model['owned_by']})")
            else:
                print(f"✗ 获取模型列表失败: {resp.status}")
        
        # 测试特定提供商模型列表
        print("\n3. 测试硅基流动提供商模型列表...")
        async with session.get(f"{base_url}/siliconflow/v1/models") as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"✓ 硅基流动模型数量: {len(result['data'])}")
                for model in result['data']:
                    print(f"  - {model['id']}")
            else:
                print(f"✗ 获取硅基流动模型列表失败: {resp.status}")
        
        # 测试消息API - 默认提供商
        print("\n4. 测试默认提供商消息API...")
        test_message = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "你好，请简单介绍一下你自己。"
                }
            ]
        }
        
        async with session.post(f"{base_url}/v1/messages", 
                               json=test_message,
                               headers={"Content-Type": "application/json"}) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"✓ 默认提供商响应成功")
                print(f"  模型: {result.get('model', 'unknown')}")
                if result.get('content') and len(result['content']) > 0:
                    text = result['content'][0].get('text', '')[:100]
                    print(f"  响应: {text}...")
            else:
                error_text = await resp.text()
                print(f"✗ 默认提供商消息API失败: {resp.status}")
                print(f"  错误: {error_text}")
        
        # 测试消息API - 指定提供商
        print("\n5. 测试硅基流动提供商消息API...")
        async with session.post(f"{base_url}/siliconflow/v1/messages", 
                               json=test_message,
                               headers={"Content-Type": "application/json"}) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"✓ 硅基流动响应成功")
                print(f"  模型: {result.get('model', 'unknown')}")
                if result.get('content') and len(result['content']) > 0:
                    text = result['content'][0].get('text', '')[:100]
                    print(f"  响应: {text}...")
            else:
                error_text = await resp.text()
                print(f"✗ 硅基流动消息API失败: {resp.status}")
                print(f"  错误: {error_text}")
        
        # 测试流式响应
        print("\n6. 测试流式响应...")
        stream_message = {**test_message, "stream": True}
        
        async with session.post(f"{base_url}/v1/messages", 
                               json=stream_message,
                               headers={"Content-Type": "application/json"}) as resp:
            if resp.status == 200:
                print("✓ 流式响应开始...")
                chunk_count = 0
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            print("  流式响应结束")
                            break
                        try:
                            chunk = json.loads(data_str)
                            chunk_count += 1
                            if chunk_count <= 3:  # 只显示前3个chunk
                                print(f"  Chunk {chunk_count}: {chunk.get('type', 'unknown')}")
                        except json.JSONDecodeError:
                            continue
                print(f"✓ 总共接收到 {chunk_count} 个数据块")
            else:
                print(f"✗ 流式响应失败: {resp.status}")

if __name__ == "__main__":
    print("Claude代理服务器测试")
    print("=" * 50)
    print("请确保代理服务器已启动 (python claude_proxy.py)")
    print("=" * 50)
    
    try:
        asyncio.run(test_proxy())
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        print("请检查:")
        print("1. 代理服务器是否已启动")
        print("2. 配置文件中的API密钥是否正确")
        print("3. 网络连接是否正常")