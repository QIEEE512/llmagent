# 前端 API 对接文档（本仓库后端实现版）

本文档面向前端联调，描述本仓库 **FastAPI** 后端当前已实现的接口、鉴权方式、请求/响应示例，以及常见坑位。

> 重要：本后端把所有接口挂载在 `/api` 下（见 `app/main.py`），所以你在浏览器/前端里访问时通常是：
>
>- `http://localhost:8080/api/...`
>
>如果你用 Vite/uni-app 开发服务器做代理、让前端从 `http://localhost:5173/api/...` 发请求，请确保 proxy 把 `/api` 转发到 `http://localhost:8080`。

---

## 0. 服务与端口

- 默认端口：`8080`
- 启动：`bash entrypoint.sh`
- Swagger：`GET http://localhost:8080/api/docs`
- OpenAPI：`GET http://localhost:8080/api/openapi.json`

### 0.1 端口占用（常见）
如果 `entrypoint.sh` 提示 `port 8080 is already in use`，说明有残留进程占用 8080。

你可以用下面命令确认占用者：

```bash
ss -ltnp | grep ':8080'
```

---

## 1. 通用约定

### 1.1 Base URL

- Base URL：`/api`

### 1.2 统一响应结构 ApiResponse

成功时：

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {}
}
```

失败时（当前项目多数接口仍使用 FastAPI 默认的错误结构）：

```json
{ "detail": "..." }
```

> 前端需要同时兼容：ApiResponse 成功体 + FastAPI 失败体（`detail`）。

### 1.3 鉴权（JWT Bearer）

需要登录的接口必须携带：

```
Authorization: Bearer <accessToken>
```

#### 1.3.1 “登录了但 /api/chat 仍 401”的排查清单（最常见）

`/api/chat` 返回：

```json
{ "detail": "未登录或登录已过期" }
```

几乎都表示 **该请求没有带上有效 Authorization header**。请按顺序自查：

1) DevTools → Network → `POST /api/chat` → Request Headers 是否有 `Authorization`
2) 是否是 `Bearer <token>`（注意 `Bearer` 后面必须有空格）
3) token 是否为空/被截断/含换行
4) chat 请求是否走了不同的 request 实例导致拦截器没注入 token

---

## 2. Auth（注册/登录/用户信息）

### 2.1 注册

- `POST /api/auth/register`
- Body（JSON）：

```json
{
  "name": "小明",
  "account": "test@example.com",
  "phone": "13800000000",
  "password": "123456"
}
```

- Response（200）：

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": { "userId": "u_xxx" }
}
```

### 2.2 登录

- `POST /api/auth/login`
- Body（JSON）：

```json
{
  "account": "1008611",
  "password": "1008611"
}
```

- Response（200）：

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "accessToken": "<JWT>",
    "tokenType": "bearer"
  }
}
```

> 注意：前端要保存 `data.accessToken`，后续接口使用 `Authorization: Bearer <accessToken>`。

### 2.3 获取当前用户

- `GET /api/auth/me`
- Header：`Authorization: Bearer <token>`
- Response（200）：

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "id": "u_xxx",
    "name": "调试用户",
    "account": "1008611"
  }
}
```

---

## 3. Accounts（子账号/档案）

> 这些接口都需要登录。

### 3.1 列表

- `GET /api/accounts`

Response：

```json
{
  "ok": true,
  "data": {
    "items": [
      { "id": "a1", "name": "小朋友", "account": "1008611" }
    ]
  }
}
```

### 3.2 创建

- `POST /api/accounts`
- Body：

```json
{ "name": "新账号名" }
```

Response：

```json
{
  "ok": true,
  "data": { "id": "a_xxx", "name": "新账号名", "account": "child_xxx" }
}
```

### 3.3 删除

- `POST /api/accounts/{accountId}/delete`

Response：

```json
{ "ok": true, "data": {} }
```

### 3.4 切换账号

- `POST /api/accounts/switch`
- Body：

```json
{ "accountId": "a1" }
```

Response：

```json
{ "ok": true, "data": { "activeAccountId": "a1" } }
```

前端切换账号后建议：
- 清空 `currentConversationId`
- 清空待发送 attachments 缓存

---

## 4. Upload（聊天附件上传）

> 需要登录。

### 4.1 上传图片

-  推荐：`POST /api/upload/image`
- 兼容旧路径：`POST /api/upload/upload/image`
- Content-Type：`multipart/form-data`
- form 字段：`file`

Response：

```json
{
  "ok": true,
  "data": {
    "url": "/files/1700000000000_xxx.png",
    "name": "xxx.png",
    "size": 123456,
    "mime": "image/png"
  }
}
```

### 4.2 上传文件

-  推荐：`POST /api/upload/file`
- 兼容旧路径：`POST /api/upload/upload/file`
- 同上

### 4.3 访问文件

- `GET /files/<name>`

> `data.url` 返回的是 `/files/<name>` 相对路径；前端展示时可以拼成完整 URL：
>
>- `http://localhost:8080/files/<name>`

---

## 5. Chat（核心对话）

> 需要登录。

### 5.1 发送对话

- `POST /api/chat`

Request Body：

```json
{
  "text": "你好",
  "conversationId": "c_xxx (可选)",
  "attachments": [
    { "type": "image", "url": "/files/a.png", "name": "a.png", "size": 123, "mime": "image/png" },
    { "type": "file",  "url": "/files/b.pdf", "name": "b.pdf", "size": 999, "mime": "application/pdf" }
  ],
  "meta": { "source": "composer" }
}
```

约束：
- `text` 允许为空字符串（仅发送附件时），但 `text` 和 `attachments` 不能同时为空
- `attachments[].type` 必须是 `image | file`
- `attachments[].url` 必须存在

Response：

```json
{
  "ok": true,
  "data": {
    "answer": "...",
    "conversationId": "c_...",
    "messageId": "m_...",
    "vision": []
  }
}
```

### 5.2 vision（图片理解）说明

后端为了避免 SSRF，只允许处理本服务上传产生的 `/files/<name>`：

- 如果 `attachments[].url` 不是 `/files/` 开头，会返回 400

---

## 6. ASR（语音识别，占位）

- `POST /api/asr`
- 需要登录

Request：

```json
{ "audioUrl": "/files/xxx.m4a" }
```

Response（当前为占位实现）：

```json
{ "ok": true, "data": { "text": "", "durationMs": null } }
```

---

## 7. Avatar（数字人）

> 需要登录。

### 7.1 上传头像

- `POST /api/avatar/upload`
- multipart/form-data，字段 `file`

Response：

```json
{
  "ok": true,
  "data": {
    "url": "/files/1700000000000_avatar.png",
    "name": "avatar.png",
    "size": 12345,
    "mime": "image/png"
  }
}
```

### 7.2 生成数字人头像

- `POST /api/avatar/generate?scope=account|user`
  - `scope=account`：按当前活跃子账号绑定
  - `scope=user`：（默认）按用户全局绑定（跨设备一致）

Request：

```json
{
  "portraitUrl": "/files/1700000000000_avatar.png",
  "profile": {
    "age": 8,
    "interests": ["math"],
    "style": "明亮、可爱",
    "freeText": "戴眼镜"
  },
  "voice": {
    "presetId": "child",
    "note": "温柔"
  },
  "output": {
    "characterStyle": "kids_cartoon"
  }
}
```

Response：

```json
{
  "ok": true,
  "data": {
    "avatarId": "av_xxx",
    "imageUrl": "/files/avatar_xxx.png",
    "url": "/files/avatar_xxx.png",
    "scope": "user"
  }
}
```

### 7.3 获取当前头像

- `GET /api/avatar/active?scope=account|user`

Response：

```json
{
  "ok": true,
  "data": {
    "avatarId": "av_xxx",
    "imageUrl": "/files/avatar_xxx.png",
    "portraitUrl": "/files/origin_xxx.png",
    "profile": { "age": 8, "interests": ["math"], "style": "", "freeText": "" },
    "voice": { "presetId": "child", "note": "" },
    "createdAt": 1700000000,
    "scope": "user"
  }
}
```

---

## 8. 前端实现建议（落地清单）

1) 做一个统一的 request 封装：
   - baseURL = `/api`
   - 每次请求从 store/storage 读取 token，自动注入 `Authorization`

2) 上传流程：
   - 先 `POST /api/upload/upload/image` 或 `/api/upload/upload/file`
   - 把返回的 `data` 映射为聊天 `attachments[]`

3) chat：
   - 首次不传 `conversationId`
   - 保存 `data.conversationId` 用于续聊

4) 错误处理：
   - 401：提示重新登录
   - 400：提示参数错误（常见于 attachments 不合法）
   - 404：对话不存在（conversationId 错/越权）
   - 503：DB 不可用（目前部分接口有此返回）
