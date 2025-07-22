#!/usr/bin/env python3
"""
Claude API代理服务器
将OpenAI兼容接口转换为Claude接口格式
"""

import json
import asyncio
import aiohttp
from aiohttp import web, ClientSession
import logging
from typing import Dict, Any, Optional
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaudeProxy:
    def __init__(self, config_path: str = "config.json"):
        self.config = self.load_config(config_path)
        self.session: Optional[ClientSession] = None
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    async def init_session(self):
        """初始化HTTP会话"""
        if not self.session:
            self.session = ClientSession()
    
    async def close_session(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
    
    def claude_to_openai_messages(self, claude_messages: list) -> list:
        """将Claude消息格式转换为OpenAI格式"""
        openai_messages = []
        
        for msg in claude_messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, list):
                    # 处理多模态内容
                    text_parts = []
                    for part in content:
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    content = "\n".join(text_parts)
                
                openai_messages.append({
                    "role": "user",
                    "content": content
                })
            elif msg.get("role") == "assistant":
                openai_messages.append({
                    "role": "assistant", 
                    "content": msg.get("content", "")
                })
        
        return openai_messages
    
    def get_provider_config(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """获取提供商配置"""
        if not provider_name:
            provider_name = self.config.get("default_provider", "siliconflow")
        
        provider_config = self.config["providers"].get(provider_name)
        if not provider_config:
            raise ValueError(f"未找到提供商配置: {provider_name}")
        
        return provider_config
    
    async def handle_messages(self, request):
        """处理Claude消息API请求"""
        try:
            await self.init_session()
            
            # 解析请求
            claude_request = await request.json()
            logger.info(f"收到Claude请求: {claude_request}")
            
            # 从URL路径中获取提供商名称
            provider_name = request.match_info.get('provider')
            if not provider_name:
                # 如果URL中没有指定提供商，使用默认提供商
                provider_name = self.config.get("default_provider")
            
            # 获取模型和提供商配置
            claude_model = claude_request.get("model")

            logger.info(f"使用提供商: {provider_name}, 使用模型: {claude_model}")
            
            provider_config = self.get_provider_config(provider_name)
            
            # 映射模型
            openai_model = provider_config["models"].get(claude_model) or provider_config["models"].get("default")
            logger.info(f"映射后的模型: {openai_model}")
            
            # 转换消息格式
            claude_messages = claude_request.get("messages", [])
            openai_messages = self.claude_to_openai_messages(claude_messages)
            
            # 处理max_tokens：如果配置文件中有设置，强制覆盖请求参数
            config_max_tokens = self.config.get("server", {}).get("max_tokens")
            if config_max_tokens is not None:
                # 配置文件中有设置，强制使用配置文件的值
                max_tokens = config_max_tokens
                logger.info(f"强制使用配置文件中的max_tokens: {max_tokens}")
            else:
                # 配置文件中没有设置，使用请求参数或默认值
                max_tokens = claude_request.get("max_tokens")
            
            # 构建OpenAI请求
            openai_request = {
                "model": openai_model,
                "messages": openai_messages,
                "stream": claude_request.get("stream", False),
                "max_tokens": max_tokens,
                "temperature": claude_request.get("temperature", 0.7)
            }
            
            logger.info(f"使用max_tokens: {max_tokens}")
            
            # 发送请求到上游API
            headers = {
                "Authorization": f"Bearer {provider_config['api_key']}",
                "Content-Type": "application/json"
            }
            
            url = f"{provider_config['base_url']}/chat/completions"
            
            if openai_request["stream"]:
                return await self.handle_stream_response(request, url, openai_request, headers)
            else:
                return await self.handle_normal_response(url, openai_request, headers)
                
        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return web.json_response({
                "error": {
                    "type": "internal_error",
                    "message": str(e)
                }
            }, status=500)
    
    async def handle_normal_response(self, url: str, request_data: dict, headers: dict):
        """处理非流式响应"""
        async with self.session.post(url, json=request_data, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"上游API错误: {resp.status} - {error_text}")
                return web.json_response({
                    "error": {
                        "type": "api_error",
                        "message": f"上游API错误: {error_text}"
                    }
                }, status=resp.status)
            
            openai_response = await resp.json()
            
            # 转换为Claude响应格式
            claude_response = self.openai_to_claude_response(openai_response)
            
            return web.json_response(claude_response)
    
    async def handle_stream_response(self, request, url: str, request_data: dict, headers: dict):
        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'X-Accel-Buffering': 'no',
            }
        )
        await response.prepare(request)

        async with self.session.post(url, json=request_data, headers=headers) as resp:
            logger.info("上游状态：%s, headers=%s", resp.status, resp.headers)
            if resp.status != 200:
                text = await resp.text()
                error_event = json.dumps({"type": "error", "error": {"message": text}})
                await response.write(f"event: error\ndata: {error_event}\n\n".encode())
                return response

            logger.info("开始处理流式响应...")

            # 发送 message_start 和 content_block_start
            message_id = f"msg_{int(time.time()*1000)}"
            msg_start = {
                "type": "message_start",
                "message": {
                    "id": message_id,
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": request_data.get("model"),
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0}
                }
            }
            await response.write(f"event: message_start\ndata: {json.dumps(msg_start)}\n\n".encode())

            content_start = {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""}
            }
            await response.write(f"event: content_block_start\ndata: {json.dumps(content_start)}\n\n".encode())
            await response.write(f"event: ping\ndata: ping\n\n".encode())
            await response.drain()

            final_stop = "end_turn"

            done = False
            async for chunk in resp.content.iter_any():
                if not chunk:
                    continue
                text = chunk.decode(errors="ignore")
                for raw in text.splitlines():
                    logger.info("⬢ raw: %r", raw)
                    if not raw.startswith("data:"):
                        continue
                    payload = raw[5:].strip()
                    if payload == "[DONE]":
                        done = True
                        break
                    try:
                        data = json.loads(payload)
                    except:
                        continue
                    ch = data.get("choices", [{}])[0]
                    if delta := ch.get("delta", {}):
                        if content := delta.get("content"):
                            ev = {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":content}}
                            # logger.info("⬢ content: %r", content)
                            await response.write(f"event: content_block_delta\ndata: {json.dumps(ev)}\n\n".encode())
                            # 插入 ping
                            # await response.write(f"event: ping\ndata: {{}}\n\n".encode())
                    if finish := ch.get("finish_reason"):
                        final_stop = {"length":"max_tokens","tool_calls":"tool_use","function_call":"tool_use","stop":"end_turn"}.get(finish,"end_turn")
                        done = True
                        break
                await response.drain()
                if done:
                    break

            # 最后记得结束事件
            await response.write(f"event: content_block_stop\ndata: {json.dumps({'type':'content_block_stop','index':0})}\n\n".encode())
            await response.write(f"event: message_delta\ndata: {json.dumps({'type':'message_delta','delta':{'stop_reason':final_stop,'stop_sequence':None}, 'usage':{'output_tokens':0}})}\n\n".encode())
            await response.write(f"event: message_stop\ndata: {{}}\n\n".encode())
            await response.write_eof()
            
        return response
    
    def openai_to_claude_response(self, openai_response: dict) -> dict:
        """将OpenAI响应转换为Claude格式"""
        choice = openai_response.get("choices", [{}])[0]
        message = choice.get("message", {})
        
        claude_response = {
            "id": f"msg_{openai_response.get('id', 'unknown')}",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": message.get("content", "")
                }
            ],
            "model": openai_response.get("model", "claude-3-haiku"),
            "stop_reason": "end_turn" if choice.get("finish_reason") == "stop" else "max_tokens",
            "stop_sequence": None,
            "usage": {
                "input_tokens": openai_response.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": openai_response.get("usage", {}).get("completion_tokens", 0)
            }
        }
        
        return claude_response
    
    def openai_to_claude_stream_chunk(self, openai_chunk: dict) -> dict:
        """将OpenAI流式响应块转换为Claude格式"""
        choice = openai_chunk.get("choices", [{}])[0]
        delta = choice.get("delta", {})
        
        if "content" in delta:
            return {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "text_delta",
                    "text": delta["content"]
                }
            }
        elif choice.get("finish_reason"):
            return {
                "type": "message_delta",
                "delta": {
                    "stop_reason": "end_turn" if choice["finish_reason"] == "stop" else "max_tokens",
                    "stop_sequence": None
                }
            }
        else:
            return {
                "type": "message_start",
                "message": {
                    "id": f"msg_{openai_chunk.get('id', 'unknown')}",
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": openai_chunk.get("model", "claude-3-haiku"),
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0}
                }
            }
    
    async def handle_health(self, request):
        """健康检查端点"""
        return web.json_response({"status": "ok", "timestamp": int(time.time())})
    
    async def handle_models(self, request):
        """模型列表端点"""
        # 从URL路径中获取提供商名称
        provider_name = request.match_info.get('provider')
        
        models = []
        if provider_name:
            # 如果指定了提供商，只返回该提供商的模型
            provider_config = self.config["providers"].get(provider_name)
            if provider_config:
                for claude_model in provider_config["models"].keys():
                    models.append({
                        "id": claude_model,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": provider_name
                    })
        else:
            # 如果没有指定提供商，返回所有提供商的模型
            for prov_name, provider_config in self.config["providers"].items():
                for claude_model in provider_config["models"].keys():
                    models.append({
                        "id": claude_model,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": prov_name
                    })
        
        return web.json_response({"data": models})
    
    def create_app(self):
        """创建Web应用"""
        app = web.Application()
        
        # 添加路由 - 支持动态提供商路径
        # 默认路由 (使用default_provider)
        app.router.add_post('/v1/messages', self.handle_messages)
        app.router.add_get('/v1/models', self.handle_models)
        
        # 动态提供商路由
        app.router.add_post('/{provider}/v1/messages', self.handle_messages)
        app.router.add_get('/{provider}/v1/models', self.handle_models)
        
        # 健康检查
        app.router.add_get('/health', self.handle_health)
        
        # 添加CORS支持
        @web.middleware
        async def cors_handler(request, handler):
            # 处理预检请求
            if request.method == 'OPTIONS':
                response = web.Response()
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Provider'
                return response
            
            # 处理正常请求
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Provider'
            return response
        
        app.middlewares.append(cors_handler)
        
        return app
    
    async def start_server(self):
        """启动服务器"""
        app = self.create_app()
        
        host = self.config["server"]["host"]
        port = self.config["server"]["port"]
        
        logger.info(f"启动Claude代理服务器: http://{host}:{port}")
        logger.info(f"支持的提供商: {list(self.config['providers'].keys())}")
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        return runner

async def main():
    """主函数"""
    proxy = ClaudeProxy()
    runner = None
    
    try:
        runner = await proxy.start_server()
        logger.info("服务器启动成功，按Ctrl+C停止")
        
        # 保持服务器运行
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器错误: {e}")
    finally:
        if runner:
            await runner.cleanup()
        await proxy.close_session()

if __name__ == "__main__":
    asyncio.run(main())