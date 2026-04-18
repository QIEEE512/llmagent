# 语音录音上传 & Qwen 语音理解对话（前后端对接说明）

本文档描述 uni-app 前端“语音按钮”的实现方式，以及后端需要提供的接口：

1) 上传录音文件（multipart）
2) 调用 Qwen 语音理解模型进行对话/转写，返回文本用于继续 chat

> 风格与现有项目保持一致：统一 `/api` 前缀、统一 `ApiResponse` 返回格式、鉴权 Bearer Token。

---

## 0. 前端实现概览

前端页面：`src/pages/chat/index.vue`

交互流程：
1. 用户点击麦克风按钮
2. 录音（最长 15s）：
   - APP 优先用 `plus.audio.getRecorder()`
   - 其它端用 `uni.getRecorderManager()`
3. 录音结束生成临时文件 `filePath`
4. 调用 `POST /api/upload/voice` 上传录音文件（字段名 `file`）
5. 拿到 `voiceUrl`（通常 `/files/...`）
6. 调用 `POST /api/voice/chat`，后端用 Qwen 语音理解模型得到文本
7. 前端将返回文本填入输入框，用户可直接点发送进入 `/api/chat`

---

## 1. 通用约定

### 1.1 鉴权

除非特别说明，接口均需登录：

- Header: `Authorization: Bearer <token>`

### 1.2 统一返回结构 ApiResponse

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {}
}
```

> 前端判定成功：`statusCode===200 && body.ok===true`

### 1.3 静态文件访问

后端需提供静态文件访问：

- `GET /files/<path>`：匿名可访问

上传成功返回 `data.url` 通常为 `/files/...`。

---

## 2. 上传录音文件

### 2.1 接口

`POST /api/upload/voice`

### 2.2 Content-Type

- `multipart/form-data`

### 2.3 Form 字段

- 字段名固定：`file`

### 2.4 音频格式建议

前端尽量录制：
- `aac`（默认）

后端建议兼容：
- `audio/aac`
- `audio/mp4`
- `audio/mpeg`（如某些端导出 mp3）

### 2.5 响应 data

成功时 `data` 建议返回：

```json
{
  "url": "/files/voice/xxx.aac",
  "name": "xxx.aac",
  "size": 12345,
  "mime": "audio/aac"
}
```

---

## 3. 语音理解对话（Qwen）

### 3.1 接口

`POST /api/voice/chat`

> 前端封装：`apiVoiceChat({ voiceUrl, conversationId?, meta? })`，超时 60s。

### 3.2 请求 JSON

```json
{
  "voiceUrl": "/files/voice/xxx.aac",
  "conversationId": "optional",
  "meta": {
    "source": "voice"
  }
}
```

- `voiceUrl`（必填）：必须是本服务上传返回的 `/files/...` URL
- `conversationId`（可选）：用于多轮语音对话记忆

### 3.3 响应 JSON

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "conversationId": "c_123",
    "text": "把语音内容转成的文本/或语音理解后的回复",
    "answer": "（可选）直接返回对用户的回复",
    "meta": {
      "model": "qwen-audio",
      "durationMs": 8230
    }
  }
}
```

前端使用约定：
- 优先取 `data.text`，其次取 `data.answer`
- 如果返回 `conversationId`，前端会缓存用于后续请求

### 3.4 错误码建议

- 400：缺少 voiceUrl
- 401：未登录
- 404：voiceUrl 不存在
- 415：不支持的音频类型
- 413：音频过大
- 422：音频解码/识别失败

---

## 4. 备注：与 /api/asr 的关系

项目里仍保留旧的 `POST /api/asr`（可选）：
- 用于“语音 -> 文字”

但本次建议走 `/api/voice/chat`：
- 让后端直接调用 qwen 语音理解进行对话
- 返回的文本可用于继续 `/api/chat`
