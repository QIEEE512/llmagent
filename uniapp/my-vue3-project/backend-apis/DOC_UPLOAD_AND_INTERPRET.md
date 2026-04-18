# 文件上传 & AI 文档解读（前后端对接说明）

本文档描述 uni-app（H5/小程序/APP）前端对 **PDF/Word/Excel** 文档上传，以及“AI 模型解读文档”的接口对接约定。

> 约定风格与现有接口保持一致：统一 `/api` 前缀、统一 `ApiResponse` 返回格式、鉴权 Bearer Token。

---

## 0. 通用约定

### 0.1 Base URL

- 开发（H5 localhost）：前端请求相对路径 `/api/...`，通过 Vite proxy 转发到后端域名。
- 生产/非 H5：`https://<your-host>/api/...`

### 0.2 鉴权

除非特别说明，接口均需登录：

- Header: `Authorization: Bearer <token>`

401 返回建议：

```json
{"detail":"未登录或登录已过期"}
```

### 0.3 统一返回结构 ApiResponse

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {}
}
```

失败：

```json
{
  "ok": false,
  "code": 40001,
  "message": "error message",
  "data": null
}
```

> 前端当前实现：当 `statusCode===200 && body.ok===true` 才判定成功。

### 0.4 静态文件访问

后端必须提供静态文件访问能力：

- `GET /files/<path>`：匿名可访问

前端会把上传成功返回的 `data.url`（通常是 `/files/...`）用于展示与后续解读。

---

## 1. 上传文档（PDF/Word/Excel）

### 1.1 接口

`POST /api/upload/file`

> 前端已实现并在聊天页“文件按钮”使用。

### 1.2 Content-Type

- `multipart/form-data`

### 1.3 Form 字段

- 字段名固定：`file`
- 单文件上传

### 1.4 文件类型限制（建议）

前端会尽量限制选择：

- 扩展名：`pdf/doc/docx/xls/xlsx`
- MIME（可能因平台不同而缺失/不准确，后端必须做最终校验）：
  - `application/pdf`
  - `application/msword`
  - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - `application/vnd.ms-excel`
  - `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

建议后端返回：
- 415：不支持的媒体类型
- 413：文件过大

### 1.5 响应 data

成功时 `data` 建议返回：

```json
{
  "url": "/files/xxx.pdf",
  "name": "xxx.pdf",
  "size": 12345,
  "mime": "application/pdf"
}
```

> 这里与现有图片上传返回结构保持一致。

---

## 2. AI 文档解读（新增）

### 2.1 目标

前端流程：
1) 先调用 `/api/upload/file` 上传文档，拿到 `fileUrl`（通常 `/files/...`）
2) 再调用“文档解读”接口，让 AI 对该文档进行总结/问答/提取要点等

### 2.2 接口（建议路径）

`POST /api/doc/interpret`

> 前端已预留 `apiDocInterpret(payload)`，请求路径为 `/doc/interpret`，超时 60s。

### 2.3 请求 JSON

```json
{
  "fileUrl": "/files/xxx.pdf",
  "fileName": "xxx.pdf",
  "fileSize": 12345,
  "fileMime": "application/pdf",
  "question": "请总结这份文档的核心要点",
  "conversationId": "optional"
}
```

字段说明：
- `fileUrl`（必填）：必须是本服务上传返回的 `/files/` 地址
- `question`（可选）：用户提问；为空时可默认做摘要/提纲
- `conversationId`（可选）：用于多轮解读记忆（与 chat 体系一致时）

### 2.4 响应 JSON

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "conversationId": "c_123",
    "answer": "...解读结果...",
    "meta": {
      "pages": 12,
      "model": "xxx",
      "tokens": 1234
    }
  }
}
```

前端展示原则：
- `data.answer` 或 `data.text` 作为主要文本
- 若返回 `conversationId`，前端会缓存用于后续追问

### 2.5 错误码建议

- 400：参数缺失（如 fileUrl）
- 401：未登录
- 404：fileUrl 不存在
- 415：文件类型不支持
- 422：文档解析失败（格式损坏/加密/受保护）
- 413：过大

---

## 3. 与现有 Chat 接口的关系（建议）

如果你更希望“解读文档”复用 `/api/chat/chat`：
- 也可以把文档作为 `attachments` 传入 chat
- 但建议仍保留专用接口 `/api/doc/interpret`，便于区分慢任务、返回结构、计费统计等

---

## 4. 前端现状（供后端确认）

- 上传：已接入 `POST /api/upload/file`（字段名 `file`，返回 `ApiResponse.data.url`）
- 选择限制：聊天页文件按钮已限制 pdf/doc/docx/xls/xlsx（仍以服务端校验为准）
- 文档解读：已预留 `POST /api/doc/interpret`（后端实现后即可联调）
