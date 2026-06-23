# 🎓 llmagent - 数字学习助手项目

<div align="center">

![Python](https://img.shields.io/badge/Python-91.4%25-blue)
![Vue](https://img.shields.io/badge/Vue-3-green)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

## 📋 项目简介

**llmagent** 是一个基于大语言模型的数字学习助手系统，包含**后端服务** + **多端前端**，为用户提供：

- 🤖 **智能对话** - 基于通义千问(Qwen)的多轮会话
- 🎭 **数字人形象** - AI 生成卡通形象和虚拟视频
- 📊 **成长档案** - 自动生成、保存和分享学习成长记录
- 🗣️ **语音交互** - ASR 语音识别和 TTS 文本转语音
- 📱 **多端支持** - 一套代码运行在 H5、iOS、Android 等平台

---

## 🏗️ 项目架构

### 整体结构

```
llmagent/
├── project/                 # 后端服务（FastAPI）
│   ├── app/
│   │   ├── main.py         # 应用入口、路由挂载
│   │   ├── config.py       # 环境配置
│   │   ├── db.py           # MongoDB 连接
│   │   ├── security.py     # JWT 认证
│   │   ├── schemas.py      # Pydantic 数据模型
│   │   ├── routers/        # API 接口层
│   │   │   ├── auth.py     # 登录/注册
│   │   │   ├── chat.py     # 对话接口
│   │   │   ├── avatar.py   # 数字人相关
│   │   │   ├── upload.py   # 文件上传
│   │   │   ├── asr.py      # 语音识别
│   │   │   └── ...
│   │   └── services/       # 业务逻辑层
│   │       ├── ai.py       # 大模型调用
│   │       ├── rag.py      # 检索增强
│   │       ├── wanx.py     # 图像/视频生成
│   │       └── ...
│   └── scripts/            # 调试脚本
│
├── uniapp/                  # 前端项目（uni-app + Vue3）
│   ├── src/
│   │   ├── pages/          # 业务页面
│   │   ├── services/       # API 和存储层
│   │   ├── components/     # 可复用组件
│   │   └── utils/          # 工具函数
│   └── vite.config.js      # Vite 构建配置
│
└── 📄 文档与资源
    ├── 服务端框架.txt      # 后端架构说明
    ├── 前端框架说明.txt    # 前端架构说明
    └── 客户端app功能说明.pptx
```

---

## 🛠️ 技术栈

### 后端（Backend）

| 技术 | 说明 |
|------|------|
| **FastAPI** | 现代高性能 Web 框架 |
| **Uvicorn** | ASGI 异步服务器 |
| **MongoDB** | NoSQL 数据库（用户、会话、消息存储） |
| **JWT** | Bearer Token 身份认证 |
| **Pydantic** | 数据验证和序列化 |
| **PyMongo** | MongoDB Python 驱动 |
| **Qwen API** | 通义千问大语言模型 |
| **Python** | 91.4% 代码占比 |

### 前端（Frontend）

| 技术 | 说明 |
|------|------|
| **uni-app** | 一套代码多端的跨平台框架 |
| **Vue 3** | 渐进式 JavaScript 框架 |
| **Vite** | 下一代前端构建工具 |
| **uview-plus** | 跨平台 UI 组件库 |
| **JavaScript** | 前端逻辑（Vue + JS） |

---

## 🚀 快速开始

### 前置要求

- **Python** >= 3.8
- **Node.js** >= 14
- **MongoDB** （本地或云服务）
- **Git**

### 后端启动

```bash
# 1. 进入后端目录
cd project

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量（可选）
# 创建 .env 文件或设置环境变量
export APP_MONGODB_URI="mongodb://localhost:27017"
export APP_MONGODB_DB="digital_teacher"
export APP_JWT_SECRET="your-secret-key"
export APP_DASHSCOPE_API_KEY="your-qwen-api-key"

# 4. 启动服务
bash entrypoint.sh
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**服务启动后访问：**
- 🔗 Swagger API 文档：http://localhost:8080/api/docs
- 🔗 OpenAPI JSON：http://localhost:8080/api/openapi.json
- 🔗 静态文件服务：http://localhost:8080/files/

### 前端启动

```bash
# 1. 进入前端目录
cd uniapp

# 2. 安装依赖
npm install

# 3. 开发模式运行（H5）
npm run dev:h5

# 4. 其他平台
# iOS/Android: npm run dev:app
# 小程序: npm run dev:mp-weixin
```

---

## 📖 核心功能模块

### 1️⃣ 认证模块 (Authentication)

**端点：** `POST /api/auth/register`, `POST /api/auth/login`

- ✅ 用户注册和登录
- ✅ JWT Token 生成和验证
- ✅ Bearer Token 鉴权

**请求示例：**
```bash
curl -X POST "http://localhost:8080/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass123"}'
```

### 2️⃣ 智能对话 (Chat)

**端点：** `POST /api/chat`

- 🤖 基于 Qwen 大模型的多轮对话
- 💾 对话历史自动保存至 MongoDB
- 📎 支持文本、图片、文件等多模态输入
- 🔐 需要 Bearer Token 认证

**请求示例：**
```json
{
  "content": "请问 Python 如何实现并发编程？",
  "conversationId": "conv_123",
  "attachments": []
}
```

### 3️⃣ 数字人形象 (Avatar)

**端点：** `POST /api/avatar/upload`, `POST /api/avatar/generate`

- 👤 上传头像图片
- 🎬 AI 生成虚拟形象和视频
- 📹 支持视频导出和分享

### 4️⃣ 成长档案 (Profile Story)

**端点：** `/api/profile/story/generate`, `/api/profile/story/list`

- 📊 自动生成学习成长档案
- 💾 档案保存和版本管理
- 📤 档案导出为 PDF/Word
- 🔗 生成分享链接

### 5️⃣ 文件上传 (Upload)

**端点：** `POST /api/upload/image`, `POST /api/upload/file`

- 📁 支持图片、文档上传
- ☁️ 自动同步至 OSS
- 🔐 上传需要认证

### 6️⃣ 语音交互 (Voice/ASR)

**端点：** `POST /api/asr`, `POST /api/voice/tts`

- 🎙️ 语音转文本 (ASR)
- 🔊 文本转语音 (TTS)
- 🌐 支持多语言

---

## 🔌 API 接口总览

### 用户与认证

```
POST   /api/auth/register              用户注册
POST   /api/auth/login                 用户登录
GET    /api/auth/me                    获取当前用户信息
```

### 对话与会话

```
POST   /api/chat                       发送消息（需要 Token）
GET    /api/chat/history               获取对话历史
GET    /api/conversations              获取会话列表
DELETE /api/conversations/{id}         删除会话
```

### 推荐问题

```
GET    /api/recommendations            获取推荐问题列表
```

### 数字人相关

```
POST   /api/avatar/upload              上传头像
POST   /api/avatar/generate            生成虚拟形象
GET    /api/avatar/{id}                获取形象详情
```

### 成长档案

```
POST   /api/profile/story/generate     生成档案
GET    /api/profile/story/list         获取档案列表
GET    /api/profile/story/{id}         获取档案详情
POST   /api/profile/story/{id}/export  导出档案
POST   /api/profile/share              创建分享链接
```

### 文件操作

```
POST   /api/upload/image               上传图片
POST   /api/upload/file                上传文件
GET    /files/{filename}               下载文件
```

### 语音处理

```
POST   /api/asr                        语音转文本
POST   /api/voice/tts                  文本转语音
```

---

## ⚙️ 环境配置

### 后端环境变量

在 `project/.env` 或系统环境变量中配置：

```bash
# MongoDB 配置
APP_MONGODB_URI=mongodb://localhost:27017
APP_MONGODB_DB=digital_teacher

# JWT 认证
APP_JWT_SECRET=your-super-secret-key-change-in-production
APP_JWT_ALGORITHM=HS256
APP_TOKEN_EXPIRE_MINUTES=1440

# 阿里云通义千问
APP_DASHSCOPE_API_KEY=your-qwen-api-key

# OSS 配置（可选）
APP_OSS_BUCKET=your-bucket
APP_OSS_REGION=oss-cn-shanghai

# 服务配置
APP_HOST=0.0.0.0
APP_PORT=8080
APP_DEBUG=false
```

### 前端环境变量

在 `uniapp/.env` 中配置：

```bash
VITE_API_BASE_URL=http://localhost:8080/api
VITE_ENABLE_MOCK=false
VITE_LOG_LEVEL=info
```

---

## 🏃 项目现状（阶段 1）

### ✅ 已实现

- ✅ FastAPI 后端框架搭建
- ✅ JWT 认证系统
- ✅ 用户登录/注册接口
- ✅ 基础对话接口（占位 AI 回复）
- ✅ 对话历史 MongoDB 持久化
- ✅ 文件上传功能
- ✅ 推荐问题接口
- ✅ ASR/Avatar 占位接口
- ✅ uni-app 多端前端框架
- ✅ 前端聊天页面
- ✅ 数字人形象定制页面
- ✅ 成长档案生成页面

### 🔜 待完善（下一阶段）

- 🔜 接入 **Qwen-Max** 真实 AI 能力
- 🔜 支持 **多轮会话** 和上下文关联
- 🔜 接入通义千问 **语音识别** (ASR)
- 🔜 文生图/视频能力（万象/Wanx）
- 🔜 **RAG** 检索增强（向量数据库）
- 🔜 完整的 **档案导出** 功能
- 🔜 增加 **限流**、统一错误码
- 🔜 性能优化和缓存策略
- 🔜 完整的单元测试和集成测试

---

## 📂 主要文件说明

### 后端关键文件

| 文件 | 说明 |
|------|------|
| `project/app/main.py` | FastAPI 应用入口，路由挂载、中间件配置 |
| `project/app/config.py` | 配置管理，环境变量读取 |
| `project/app/db.py` | MongoDB 连接池管理 |
| `project/app/security.py` | JWT 生成、密码哈希等安全相关 |
| `project/app/schemas.py` | Pydantic 数据模型定义 |
| `project/app/routers/` | 各模块 API 接口 |
| `project/app/services/` | 业务逻辑层，调用外部 API |

### 前端关键文件

| 文件 | 说明 |
|------|------|
| `uniapp/src/pages.json` | 页面路由配置 |
| `uniapp/src/main.js` | Vue 应用入口 |
| `uniapp/src/pages/` | 各业务页面 |
| `uniapp/src/services/http.js` | HTTP 请求封装 |
| `uniapp/src/services/api.js` | 业务 API 函数集合 |
| `uniapp/vite.config.js` | Vite 构建配置 |

---

## 🧪 调试脚本

项目提供了多个调试脚本在 `project/scripts/` 目录下，帮助快速定位问题：

| 脚本 | 用途 |
|------|------|
| `debug_asr_env.py` | 检查 ASR 环境和依赖 |
| `debug_chat_history.py` | 排查对话历史问题 |
| `debug_chat_vision_flow.py` | 验证图像输入流程 |
| `debug_doc_interpret.py` | 验证文档理解接口 |
| `debug_embeddings.py` | 检查向量/Embedding 调用 |
| `test_qwen.py` | 测试 Qwen 模型连通性 |
| `wanx_i2v_audio_demo.py` | 独立测试视频生成能力 |

**运行调试脚本：**
```bash
cd project
python scripts/test_qwen.py
```

---

## 📊 数据库设计

### MongoDB Collections

**users**
```json
{
  "_id": ObjectId,
  "username": "string",
  "email": "string",
  "hashed_password": "string",
  "created_at": ISODate,
  "updated_at": ISODate
}
```

**conversations**
```json
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "title": "string",
  "created_at": ISODate,
  "updated_at": ISODate
}
```

**messages**
```json
{
  "_id": ObjectId,
  "conversation_id": ObjectId,
  "user_id": ObjectId,
  "content": "string",
  "role": "user|assistant",
  "created_at": ISODate
}
```

---

## 🔐 安全建议

- 🔑 **JWT_SECRET** 必须在生产环境修改
- 🛡️ 启用 **CORS** 白名单
- 🔒 使用 **HTTPS** 传输敏感数据
- 📋 添加 **请求限流** (Rate Limiting)
- 🗂️ 定期备份 **MongoDB** 数据
- 🚨 添加 **请求日志** 和异常监控

---

## 📝 开发规范

### 后端代码规范

```python
# 1. 使用类型注解
def get_user(user_id: str) -> User:
    pass

# 2. 异常处理
try:
    result = call_external_api()
except Exception as e:
    logger.error(f"API call failed: {e}")
    raise HTTPException(status_code=500, detail="Internal error")

# 3. 日志记录
logger.info(f"User {user_id} logged in")
```

### 前端代码规范

```javascript
// 1. 使用 Script Setup
<script setup>
import { ref } from 'vue'

const message = ref('')
</script>

// 2. 异常处理
try {
  const response = await apiChat(payload)
  messages.value.push(response)
} catch (error) {
  uni.showToast({ title: error.message, icon: 'error' })
}

// 3. 组件命名
// components/ChatMessage.vue
// components/AvatarCard.vue
```

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙋 常见问题

### Q: 如何修改数据库连接？
A: 修改 `project/.env` 中的 `APP_MONGODB_URI` 环境变量

### Q: 前端如何切换 API 地址？
A: 修改 `uniapp/.env` 中的 `VITE_API_BASE_URL`

### Q: 如何添加新的 API 接口？
A: 
1. 在 `project/app/routers/` 新建或修改模块文件
2. 定义 Pydantic 数据模型
3. 在 `main.py` 中挂载路由

### Q: 前端打包小程序失败怎么办？
A: 检查 `uniapp/vite.config.js` 配置，确保 `@dcloudio/vite-plugin-uni` 版本兼容

---

## 📞 联系与支持

- 📧 提交 Issue：[GitHub Issues](https://github.com/QIEEE512/llmagent/issues)
- 💬 项目讨论：[GitHub Discussions](https://github.com/QIEEE512/llmagent/discussions)

---

<div align="center">

**⭐ 如果本项目对你有帮助，请给个 Star 吧！**

Made with ❤️ by [QIEEE512](https://github.com/QIEEE512)

</div>
