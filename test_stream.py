#!/usr/bin/env python3
"""
测试流式响应的简单脚本
"""

import asyncio
import aiohttp
import json
import time

async def test_stream():
    """测试流式响应"""
    url = "http://127.0.0.1:8001/v1/messages"
    
    data = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 100,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": "请数数从1到10，每个数字单独一行"
            }
        ]
    }
    
    print("开始测试流式响应...")
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as resp:
            print(f"响应状态: {resp.status}")
            print(f"响应头: {dict(resp.headers)}")
            
            if resp.status != 200:
                error_text = await resp.text()
                print(f"错误: {error_text}")
                return
            
            chunk_count = 0
            async for line in resp.content:
                current_time = time.time()
                elapsed = current_time - start_time
                
                try:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str == '[DONE]':
                            print(f"[{elapsed:.2f}s] 流式响应结束")
                            break
                        
                        try:
                            chunk = json.loads(data_str)
                            chunk_count += 1
                            chunk_type = chunk.get('type', 'unknown')
                            
                            if chunk_type == 'content_block_delta':
                                text = chunk.get('delta', {}).get('text', '')
                                print(f"[{elapsed:.2f}s] Chunk {chunk_count}: '{text}'")
                            else:
                                print(f"[{elapsed:.2f}s] Chunk {chunk_count}: {chunk_type}")
                                
                        except json.JSONDecodeError as e:
                            print(f"[{elapsed:.2f}s] JSON解析错误: {e}")
                            
                except UnicodeDecodeError:
                    print(f"[{elapsed:.2f}s] 解码错误")
                    
            total_time = time.time() - start_time
            print(f"\n总耗时: {total_time:.2f}秒")
            print(f"总块数: {chunk_count}")

if __name__ == "__main__":
    try:
        asyncio.run(test_stream())
    except Exception as e:
        print(f"测试失败: {e}")