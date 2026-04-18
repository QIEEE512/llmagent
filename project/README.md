# 我的数字老师 - 后端（阶段 1）

本仓库已根据 `openapi.yaml`/`README copy.md` 落地一个 **FastAPI** 后端的第一阶段版本：

- ✅ 注册/登录（JWT）
- ✅ 推荐问题（mock）
- ✅ 对话接口（占位 AI 回复 + MongoDB 落库：conversation/messages）
- ✅ 上传接口（存到 `/tmp/uploads` 并以 `/files/<name>` 暴露）
- ✅ ASR / Avatar 端点（对齐响应结构的占位实现，便于前端先联调）

> 当前重点是“接口可跑、返回结构对齐、可逐步扩展”。大模型能力（qwen-max、文生图/视频、多模态 ASR）下一阶段接入。

## 运行

推荐在 Devbox 环境里直接运行：

```bash
bash entrypoint.sh
```

启动后：

- Swagger: `http://localhost:8080/api/docs`
- OpenAPI JSON: `http://localhost:8080/api/openapi.json`

## 环境变量（可选）

通过 `.env` 或环境变量覆盖（前缀 `APP_`）：

- `APP_MONGODB_URI`：MongoDB 连接串（默认 `mongodb://localhost:27017`）
- `APP_MONGODB_DB`：库名（默认 `digital_teacher`）
- `APP_JWT_SECRET`：JWT 密钥（默认 `dev-secret`，生产务必修改）
- `APP_DASHSCOPE_API_KEY`：后续接入通义千问用

## 已实现接口（阶段 1）

Base URL: `/api`

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/recommendations`
- `POST /api/chat`（需要 `Authorization: Bearer <token>`）
- `POST /api/upload/image`（需要 token）
- `POST /api/upload/file`（需要 token）
- `POST /api/asr`（需要 token，占位）
- `POST /api/avatar/upload`（需要 token）
- `POST /api/avatar/generate`（需要 token，占位）

## 待完善（下一阶段建议）

- 🔜 使用你提供的 MongoDB 连接串，补齐索引（按 `account`、`userId`、`conversationId`）
- 🔜 chat 支持真正的“多轮会话”与“继续同一 conversationId”（当前每次请求会新建会话）
- 🔜 接入 qwen-max 生成回复，并把上下文消息拼接进 prompt
- 🔜 `/asr` 接入通义千问语音/多模态能力，读取 `audioUrl` 产出 `text`
- 🔜 `/avatar/generate` 接入通义千问文生图/视频能力，产出 `avatarPngUrl`/`videoUrl`
- 🔜 增加限流、统一错误码（目前用 HTTP status + 简单 message）


整体优化流程问题整理：
头像绑定问题
账户登录问题（删除默认账户）
档案问题