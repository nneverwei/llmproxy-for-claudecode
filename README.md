# Claude API 代理服务器 🚀

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![aiohttp](https://img.shields.io/badge/aiohttp-3.8+-orange.svg)](https://aiohttp.readthedocs.io/)

> 🔄 将任何OpenAI兼容接口转换为Claude API格式，让你在Claude Code中无缝使用其他厂商的大模型服务

## ✨ 功能特性

- 🔌 **多提供商支持** - 硅基流动、OpenAI、DeepSeek等OpenAI兼容接口
- 🔄 **智能格式转换** - 自动转换Claude与OpenAI消息格式
- 🌊 **流式响应** - 完整支持实时流式对话
- 🎯 **动态路由** - 通过URL路径动态切换不同提供商
- 🗺️ **模型映射** - 灵活配置Claude模型到实际模型的映射
- 🔍 **健康监控** - 内置健康检查和模型列表端点
- 🌐 **CORS支持** - 完整的跨域资源共享支持

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API密钥

编辑 `config.json` 文件：

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8000
  },
  "providers": {
    "siliconflow": {
      "base_url": "https://api.siliconflow.cn/v1",
      "api_key": "sk-your-siliconflow-api-key",
      "models": {
        "claude-3-5-sonnet-20241022": "Qwen/Qwen2.5-14B-Instruct",
        "claude-3-opus-20240229": "Qwen/Qwen2.5-72B-Instruct"
      }
    },
    "deepseek": {
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "sk-your-deepseek-api-key",
      "models": {
        "claude-3-5-sonnet-20241022": "deepseek-chat",
        "claude-3-opus-20240229": "deepseek-coder"
      }
    }
  },
  "default_provider": "siliconflow"
}
```

### 3. 启动服务

```bash
python claude_proxy.py
```

🎉 服务器将在 `http://127.0.0.1:8000` 启动！

### 4. 在Claude Code中配置

在Claude Code设置中配置API端点：

| 提供商 | API端点 | 说明 |
|--------|---------|------|
| 默认提供商 | `http://127.0.0.1:8000/v1` | 使用配置中的默认提供商 |
| 硅基流动 | `http://127.0.0.1:8000/siliconflow/v1` | 专门使用硅基流动 |
| DeepSeek | `http://127.0.0.1:8000/deepseek/v1` | 专门使用DeepSeek |

## 📡 API端点

### 核心端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/v1/messages` | Claude消息API（默认提供商） |
| `POST` | `/{provider}/v1/messages` | 指定提供商的消息API |
| `GET` | `/v1/models` | 获取所有模型列表 |
| `GET` | `/{provider}/v1/models` | 获取指定提供商模型 |
| `GET` | `/health` | 健康检查 |

### 使用示例

#### 默认提供商
```bash
curl -X POST http://127.0.0.1:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1000,
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ]
  }'
```

#### 指定提供商（硅基流动）
```bash
curl -X POST http://127.0.0.1:8000/siliconflow/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "max_tokens": 1000,
    "stream": true,
    "messages": [
      {"role": "user", "content": "写一个Python快速排序算法"}
    ]
  }'
```

## 🧪 测试功能

运行内置测试脚本验证所有功能：

```bash
python test_proxy.py
```

测试覆盖：
- ✅ 健康检查端点
- ✅ 模型列表API
- ✅ 消息API（默认和指定提供商）
- ✅ 流式响应功能

## 🎯 支持的提供商

| 提供商 | 官网 | 特点 |
|--------|------|------|
| 🔥 硅基流动 | [siliconflow.cn](https://siliconflow.cn) | 高性价比，模型丰富 |
| 🤖 OpenAI | [openai.com](https://openai.com) | 官方GPT模型 |
| 🧠 DeepSeek | [deepseek.com](https://deepseek.com) | 强大的代码能力 |
| 📚 智谱AI | [zhipuai.cn](https://zhipuai.cn) | 中文优化模型 |
| 🌟 其他 | - | 任何OpenAI兼容接口 |

## ⚙️ 高级配置

### 模型映射

在配置文件中自定义模型映射：

```json
{
  "providers": {
    "custom_provider": {
      "base_url": "https://api.example.com/v1",
      "api_key": "your-api-key",
      "models": {
        "claude-3-haiku": "custom-fast-model",
        "claude-3-sonnet": "custom-balanced-model",
        "claude-3-opus": "custom-powerful-model"
      }
    }
  }
}
```

### 服务器配置

```json
{
  "server": {
    "host": "0.0.0.0",  // 监听所有网络接口
    "port": 8080        // 自定义端口
  }
}
```

## 🔧 项目结构

```
claude-proxy/
├── claude_proxy.py     # 主服务器代码
├── config.json         # 配置文件
├── test_proxy.py       # 测试脚本
├── requirements.txt    # Python依赖
└── README.md          # 项目文档
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## ⚠️ 注意事项

- 🔑 确保API密钥有效且有足够配额
- 🖼️ 图像处理等高级功能可能不被所有提供商支持
- 🔄 响应格式会尽可能匹配Claude API规范
- 📝 提供商名称必须与配置文件中的键名完全匹配

## 🆘 常见问题

<details>
<summary>Q: 如何添加新的API提供商？</summary>

A: 在 `config.json` 的 `providers` 部分添加新配置即可：

```json
"new_provider": {
  "base_url": "https://api.newprovider.com/v1",
  "api_key": "your-api-key",
  "models": {
    "claude-3-haiku": "provider-model-name"
  }
}
```
</details>

<details>
<summary>Q: 为什么Claude Code连接失败？</summary>

A: 请检查：
1. 代理服务器是否正常启动
2. API端点URL是否正确配置
3. 防火墙是否阻止了8000端口
4. 配置文件中的API密钥是否有效
</details>

<details>
<summary>Q: 支持哪些Claude模型？</summary>

A: 支持所有Claude模型名称，通过配置文件映射到实际的模型：
- claude-3-haiku
- claude-3-sonnet  
- claude-3-opus
- claude-3-5-sonnet
- 以及其他Claude模型
</details>

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

Made with ❤️ by developers, for developers

</div>