API_DOC.md
# 我的数字老师 - 后端接口对接文档（阶段 1）

本文档面向前端/联调使用，覆盖当前后端已落地的所有端点，并给出：

- Base URL
- 鉴权方式
- 请求字段说明
- 成功返回示例
- 失败返回示例（含典型 HTTP 状态码）

> 说明：本项目接口的标准结构来自 `openapi.yaml`。部分端点（ASR/Avatar generate）当前为占位实现，但响应结构已对齐，方便前端先接。

---

## 统一约定

### Base URL

服务根地址（你提供的线上地址）：

- `https://pkhlxjidylji.sealoshzh.site/`

Base URL（接口统一前缀）：

- `/api`

因此，前端实际请求时的完整前缀为：

- `https://pkhlxjidylji.sealoshzh.site/api`

### Content-Type

- JSON 请求：`Content-Type: application/json`
- 上传请求：`Content-Type: multipart/form-data`

### 鉴权（JWT Bearer）

登录成功后会获得 `accessToken`，后续接口在 Header 中携带：

- `Authorization: Bearer <accessToken>`

若缺少或 token 无效/过期，后端返回：

- HTTP `401`
- body（**注意：这是 FastAPI 默认错误结构**，不属于 ApiResponse）：

```json
{
  "detail": "未登录或登录已过期"
}
```

或：

```json
{
  "detail": "未登录或登录已过期"
}
```

### 通用成功响应（ApiResponse）

所有业务接口成功时返回：

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {}
}
```

其中 `data` 的结构见各接口说明。

### 通用失败响应（当前阶段）

当前阶段尚未做统一的 `ApiResponse(ok=false)` 错误封装。

- 认证类错误、参数校验失败等，通常会返回 **HTTP 4xx**，body 为 FastAPI 默认结构，例如：

认证失败：

```json
{
  "detail": "账号或密码错误"
}
```

---

## 登录页联调专用调试账号（必备）

为便于前端不依赖注册流程也能验证登录，本服务启动时会自动预置一条用户：

- account：`1008611`
- password：`1008611`

> 前端登录页默认会填充该账号。

参数校验失败（示例）：

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "account"],
      "msg": "Field required",
      "input": {"password": "123456"}
    }
  ]
}
```

> 前端对接建议：
> - 成功：以 HTTP 200 且 `ok === true` 为准
> - 失败：以 HTTP status != 200 为准，读取 `detail` 作为提示

---

## Auth

### 0) 获取当前用户信息（账户管理页建议使用）

- **GET** `/api/auth/me`
- **鉴权**：是（Bearer Token）

#### 成功返回（200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "id": "u_123",
    "name": "张三",
    "account": "1008611"
  }
}
```

#### 失败返回

- 未登录/过期：HTTP `401`

```json
{ "detail": "未登录或登录已过期" }
```

### 1) 注册

- **POST** `/api/auth/register`
- **鉴权**：否

#### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| name | string | 是 | 昵称 |
| account | string | 是 | 登录账号（邮箱/用户名均可） |
| phone | string \| null | 否 | 手机号 |
| password | string | 是 | 密码 |

#### 成功返回（200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "userId": "u_123..."
  }
}
```

#### 失败返回

- 账号已存在：HTTP `400`
- 账号已存在：HTTP `409`

```json
{
  "detail": "账号已存在"
}
```

---

### 2) 登录

- **POST** `/api/auth/login`
- **鉴权**：否

#### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| account | string | 是 | 账号 |
| password | string | 是 | 密码 |

#### 成功返回（200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "accessToken": "<jwt>",
    "tokenType": "bearer"
  }
}
```

#### 失败返回

- 账号或密码错误：HTTP `401`

```json
{
  "detail": "账号或密码错误"
}
```

---

## Accounts（账户管理页）

> 当前策略：单账号（一个用户仅一个账号）。
> - 列表接口始终返回 1 个账号（若历史数据为空，后端会自动补一个默认账号）
> - 新增第二个账号会返回 409
> - 删除账号不支持（409）
> - 切换账号接口保留兼容，但在单账号模式下为 no-op

> 以下接口均需要 token。

### 1) 获取账户列表

- **GET** `/api/accounts`
- **鉴权**：是

#### 成功返回（200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      { "id": "a1", "name": "小朋友", "account": "1008611" }
    ]
  }
}
```

#### 失败返回

- 未登录/过期：HTTP `401`

```json
{ "detail": "未登录或登录已过期" }
```

### 2) 新增账户

- **POST** `/api/accounts`
- **鉴权**：是

#### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| name | string | 是 | 新账户名称 |

```json
{ "name": "新账号名" }
```

#### 成功返回（200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": { "id": "a_xxx", "name": "新账号名", "account": "child_xxx" }
}
```

#### 失败返回

- 未登录/过期：HTTP `401`

```json
{ "detail": "未登录或登录已过期" }
```

- name 为空：HTTP `400`

```json
{ "detail": "name 不能为空" }
```

- 单账号策略（已存在账号）：HTTP `409`

```json
{ "detail": "同一用户仅允许一个账号" }
```

### 3) 删除账户

- **POST** `/api/accounts/{accountId}/delete`
- **鉴权**：是

#### 成功返回（200）

```json
{ "ok": true, "code": 0, "message": "ok", "data": {} }
```

#### 失败返回

- 未登录/过期：HTTP `401`

```json
{ "detail": "未登录或登录已过期" }
```

- 单账号策略不支持删除：HTTP `409`

```json
{ "detail": "单账号策略不支持删除账号" }
```

### 4) 切换当前账户

- **POST** `/api/accounts/switch`
- **鉴权**：是

#### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| accountId | string | 是 | 要切换到的账户ID |

```json
{ "accountId": "a1" }
```

说明：单账号模式下，此接口仅用于兼容旧前端，实际不会切换到其他账号。

#### 成功返回（200）

```json
{ "ok": true, "code": 0, "message": "ok", "data": { "activeAccountId": "a1" } }
```

#### 失败返回

- 未登录/过期：HTTP `401`

```json
{ "detail": "未登录或登录已过期" }
```

- 账户不存在：HTTP `404`

```json
{ "detail": "account not found" }
```

- 单账号策略下请求切到其他账号：HTTP `409`

```json
{ "detail": "单账号策略下不可切换到其他账号" }
```

---

## 前端改单账号策略（必做）

1) 账户列表页：
- 直接展示 `items[0]` 即可，不再提供“多账号切换器”。

2) 新建账号按钮：
- 建议隐藏；若保留，需处理 `409 同一用户仅允许一个账号`。

3) 删除账号按钮：
- 建议隐藏；若保留，需处理 `409 单账号策略不支持删除账号`。

4) 切换账号接口：
- 可以不再调用；若历史代码仍会调用，继续用当前账号 id 即可。

5) 历史数据加载失败提示：
- 401 仍按“登录失效”处理；
- 409 统一提示“当前为单账号模式，不支持该操作”。

---

## Chat

### 5) 推荐问题

- **GET** `/api/recommendations`
- **鉴权**：否

#### 成功返回（200）

```json
{
  "ok": true,
  "code": "",
  "message": "",
  "data": {
    "items": [
      {"id": "r1", "text": "帮我制定一个今天的学习计划"},
      {"id": "r2", "text": "用简单的话解释一下牛顿第二定律"}
    ]
  }
}
```

---

### 6) 发送对话

- **POST** `/api/chat`
- **鉴权**：是（Bearer Token）

#### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| text | string | 是 | 用户输入 |
| attachments | array | 否 | 附件数组 |
| meta | object | 否 | 额外信息（任意键值） |

`attachments[]`：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| type | "image" \| "file" | 是 | 附件类型 |
| url | string | 是 | 附件 url（通常来自上传接口返回） |

#### 成功返回（200）

```json
{
  "ok": true,
  "code": "",
  "message": "",
  "data": {
    "answer": "...",
    "conversationId": "c_...",
    "messageId": "m_..."
  }
}
```

#### 失败返回

- 缺少 token：HTTP `401`

```json
{
  "detail": "Missing token"
}
```

- token 无效：HTTP `401`

```json
{
  "detail": "Invalid token"
}
```

---

## Upload

> 上传接口需要 token。上传成功后会返回一个 `url`（形如 `/files/<name>`），前端可直接使用该 URL 作为附件链接。

### 7) 上传图片（聊天附件）

- **POST** `/api/upload/image`
- **鉴权**：是
- **请求类型**：`multipart/form-data`

#### 表单字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| file | file(binary) | 是 | 图片文件 |

#### 成功返回（200）

```json
{
  "ok": true,
  "code": "",
  "message": "",
  "data": {
    "url": "/files/xxxxx.png",
    "mime": "image/png",
    "size": 12345
  }
}
```

#### 失败返回

- 缺少 token：HTTP `401`
- 缺少文件字段：HTTP `422`

---

### 8) 上传文件（聊天附件）

- **POST** `/api/upload/file`
- **鉴权**：是
- **请求类型**：`multipart/form-data`

#### 表单字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| file | file(binary) | 是 | 任意文件 |

#### 成功返回（200）

返回结构同上传图片。

---

## ASR

### 9) 语音识别（语音转文字）

- **POST** `/api/asr`
- **鉴权**：是

#### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| audioUrl | string | 否 | 建议先上传音频得到 url |
| format | string | 否 | 例如 m4a |
| sampleRate | int | 否 | 例如 16000 |

#### 成功返回（200）

> 当前阶段为占位实现：`text` 为空。

```json
{
  "ok": true,
  "code": "",
  "message": "",
  "data": {
    "text": "",
    "durationMs": null
  }
}
```

---

## Avatar

### 10) 上传头像照片（数字人采集）

- **POST** `/api/avatar/upload`
- **鉴权**：是
- **请求类型**：`multipart/form-data`

#### 表单字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| file | file(binary) | 是 | 图片文件 |

#### 成功返回（200）

返回结构同上传图片：

```json
{
  "ok": true,
  "code": "",
  "message": "",
  "data": {
    "url": "/files/xxxxx.jpg",
    "mime": "image/jpeg",
    "size": 12345
  }
}
```

---

### 11) 生成数字人头像（绑定到账号或用户）

- **POST** `/api/avatar/generate`
- **鉴权**：是
- **Query**：`scope=account|user`（可选，默认 `account`）
  - `account`：按当前活跃子账号绑定（默认）
  - `user`：按用户全局绑定（跨设备一致）

#### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| portraitUrl | string | 是 | 头像原图 URL（必须为 `/files/...`） |
| profile | object | 是 | 画像资料（见下表） |
| voice | object | 是 | 声音设定（见下表） |
| output | object | 否 | 输出风格（可选） |

`profile`：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| age | int | 是 | 3~12 |
| interests | string[] | 否 | 兴趣列表 |
| style | string | 否 | 画风描述 |
| freeText | string | 否 | 其他补充 |

`voice`：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| presetId | string | 是 | 声线预设 ID |
| note | string | 否 | 备注 |

`output`：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| characterStyle | string | 否 | 输出风格（可选） |

#### 成功返回（200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "avatarId": "av_xxx",
    "imageUrl": "/files/avatar_xxx.png",
    "url": "/files/avatar_xxx.png",
    "scope": "user"
  }
}
```

### 12) 获取当前头像

- **GET** `/api/avatar/active`
- **鉴权**：是
- **Query**：`scope=account|user`（可选，默认 `account`）

#### 成功返回（200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
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

## Avatar Video

### 13) 生成头像视频（Wan2.6-I2V-Flash）

- **POST** `/api/avatar/video/generate`
- **鉴权**：是
- **Query**：`scope=account|user`（可选，默认 `account`）

说明：
- 当前仅使用“提示词生成音频”，不接收 `audioUrl`。

#### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| imageUrl | string | 否 | 头像图片 `/files/...`，不传则使用当前头像 | 
| introText | string | 否 | 自我介绍文本，用于生成声音描述 |
| prompt | string | 否 | 视频提示词 |
| resolution | string | 否 | 720P/1080P，默认 720P |
| duration | int | 否 | 时长（秒），默认 10 |
| shotType | string | 否 | 多镜头类型（默认 multi） |

#### 成功返回（200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "jobId": "vj_xxx"
  }
}
```

### 14) 查询头像视频状态

- **GET** `/api/avatar/video/status?jobId=...`
- **鉴权**：是
- **Query**：`scope=account|user`（可选，默认 `account`）

#### 成功返回（200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "jobId": "vj_xxx",
    "status": "SUCCEEDED",
    "videoUrl": "/files/avatar_video_xxx.mp4",
    "scope": "user"
  }
}
```

---

## 联调小抄（常用流程）

1. `POST /api/auth/register` 注册（可跳过）
2. `POST /api/auth/login` 登录拿 token
3. 调用需要鉴权的接口时带 header：`Authorization: Bearer ...`
4. 有图片/文件先走上传接口拿到 `url`，再放进 `chat.attachments[]`

---

## 相关链接

- OpenAPI 文件：`openapi.yaml`
- 在线 Swagger（服务启动后）：`/api/docs`