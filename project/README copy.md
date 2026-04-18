# 后端接口清单（给本项目对接用）
这是一个基于python的后端项目，我的数据库连接方式为：mongodb://root:50zm909rd59Elv9i@test-db-mongodb.ns-5g058qc1.svc:27017
我要接入通义千问文生图、语音视频多模态大模型、以及qwen-max通用大模型的回复来实现这些功能。阿里云大模型的api_key为：sk-c9ae0bc011c9400dbdc2ba0c1292776a
本文件夹用于把当前前端项目里“预留/需要”的后端接口整理成可直接抄到后端开发的规格说明。

> 说明：当前前端仍是 mock 逻辑（不真的请求）。以下接口是**建议的最小集合**，覆盖登录/注册、聊天、上传、语音识别、数字人生成。

## 统一约定

### Base URL
- 建议：`/api`

### 认证方式（建议）
- 登录成功后后端返回 `accessToken`
- 前端后续请求带：`Authorization: Bearer <accessToken>`

### 通用响应结构（建议）
```json
{
  "ok": true,
  "code": "",
  "message": "",
  "data": {}
}
```

### 错误码建议
- `AUTH_INVALID_CREDENTIALS`：账号或密码错误
- `AUTH_TOKEN_EXPIRED`：token 过期
- `VALIDATION_ERROR`：入参校验失败
- `RATE_LIMITED`：限流

## 接口列表（按业务）

### 1) 认证 Auth
- `POST /api/auth/register`  注册
- `POST /api/auth/login`     登录
- （可选）`POST /api/auth/logout` 退出登录
- （可选）`GET /api/me` 获取当前用户信息

### 2) 聊天 Chat
- `GET /api/recommendations` 推荐问题
- `POST /api/chat`           发送对话

### 3) 上传 Upload
- `POST /api/upload/image`   上传图片（聊天附件）
- `POST /api/upload/file`    上传文件（聊天附件）
- `POST /api/avatar/upload`  上传头像照片（数字人采集）

### 4) 语音 ASR
- `POST /api/asr`            语音识别（语音转文字）

### 5) 数字人 Avatar
- `POST /api/avatar/generate` 生成数字人（头像 PNG + 20 秒视频）

## 文件说明
- `openapi.yaml`：OpenAPI 3.0 规范（推荐后端直接导入 Swagger/Apifox/Postman）
- `examples/`：请求/响应示例

