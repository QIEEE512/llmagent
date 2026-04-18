# WanX 音频相关 API 核查清单（脱敏）

> 生成时间：2026-02-13  
> 目的：用于排查“视频无声”问题，汇总当前项目中**实际生效**的请求参数与完整响应字段。

## 1. 后端业务接口（本项目）

### 1.1 `POST /api/avatar/video/generate`

- 鉴权：`Authorization: Bearer <TOKEN>`
- Query：`scope=account|user`（默认 `account`）
- Content-Type：`application/json`

#### 请求体（代码实际支持字段）

```json
{
  "imageUrl": "/files/xxx.png",
  "imgUrl": "/files/xxx.png",
  "fileUrl": "/files/xxx.png",
  "url": "/files/xxx.png",
  "introText": "我是小明，喜欢数学。",
  "prompt": "让角色做自然口播动作",
  "resolution": "720P",
  "duration": 10,
  "shotType": "multi"
}
```

说明：
- `imageUrl/imgUrl/fileUrl/url` 四选一，后端会按顺序取第一个非空值。
- 仅接受 `/files/...` 本地路径，后端会上传到 OSS 再生成签名 URL 给模型使用。

#### 音频相关字段（重点）

- 当前该接口**不接收**并且不向模型透传以下字段：
  - `audio`
  - `audio_enabled`
  - `voice`
  - `audioUrl`
- 当前代码实际固定调用：
  - `audio_url=None`（未传入外部音频）
  - 通过 prompt 中的“声音描述”引导模型生成音频

#### 成功响应（HTTP 200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "jobId": "vj_<task_id>"
  }
}
```

#### 常见失败响应（HTTP + detail）

- `400`
  - `scope must be account or user`
  - `fileUrl must start with /files/`
  - `imageUrl is required (or generate an avatar first)`
  - `i2v input image is invalid or unsupported: ...InvalidParameter.DataInspection...`
- `500`
  - `video generation failed: <ExceptionType>`
  - `OSS upload failed: <ExceptionType>`
- `502`
  - DashScope 调用失败，detail 里包含 `status/code/message`
- `503`
  - `数据库不可用：...`
  - `OSS unavailable: ...`

---

### 1.2 `GET /api/avatar/video/status?jobId=...`

#### 成功响应（HTTP 200）

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "jobId": "vj_xxx",
    "status": "PENDING|RUNNING|SUCCEEDED|FAILED|CANCELED|UNKNOWN",
    "videoUrl": "/files/avatar_video_xxx.mp4",
    "scope": "account"
  }
}
```

#### 失败响应

- `400`: `jobId is required`
- `404`: `job not found`
- `502`: DashScope fetch 失败（detail 含 status/code/message）
- `503`: 数据库不可用

---

## 2. 模型层请求参数（DashScope / Wan2.6-I2V-Flash）

项目内部调用位置：`app/services/wanx.py -> wan_i2v_create_task()`

### 2.1 实际传给 `VideoSynthesis.async_call(...)` 的参数

```python
VideoSynthesis.async_call(
    api_key=<DASHSCOPE_API_KEY>,
    model="wan2.6-i2v-flash" 或 "wan2.6-i2v",
    prompt=<拼接后的提示词>,
    img_url=<OSS签名URL>,
    audio_url=None 或 <公网可访问音频URL>,
    resolution="720P",
    extend_prompt=True,
    duration=10,
    shot_type="multi"
)
```

### 2.2 音频相关字段核查

- **已支持且有效**：`audio_url`
- **当前代码未使用**：`audio`, `audio_enabled`, `voice`
- SDK 显式签名中可见 `audio_url`，未见 `audio_enabled` / `voice`。

结论：
- 若要稳定“人声对白”，建议显式传 `audio_url`。
- 仅依赖 prompt 生成音频，稳定性通常低于“外部音频驱动”。

---

## 3. DashScope 响应内容（完整字段）

> 下方示例为脱敏后的结构，包含你要求的 `HTTP状态码/code/message/request_id`。

### 3.1 `async_call` 成功（HTTP 200）

```json
{
  "request_id": "req_xxx",
  "code": null,
  "message": "",
  "output": {
    "task_id": "966cebcd-dedc-4962-af88-xxxxxx",
    "task_status": "PENDING"
  },
  "usage": {
    "video_count": 1
  }
}
```

### 3.2 `fetch` 进行中（HTTP 200）

```json
{
  "request_id": "req_xxx",
  "code": null,
  "message": "",
  "output": {
    "task_id": "966cebcd-dedc-4962-af88-xxxxxx",
    "task_status": "RUNNING",
    "video_url": ""
  }
}
```

### 3.3 `fetch` 成功（HTTP 200）

```json
{
  "request_id": "c1209113-8437-424f-a386-xxxxxx",
  "code": null,
  "message": "",
  "output": {
    "task_id": "966cebcd-dedc-4962-af88-xxxxxx",
    "task_status": "SUCCEEDED",
    "video_url": "https://dashscope-result-xxx/xxx.mp4?Expires=***&Signature=***"
  }
}
```

### 3.4 `fetch` 失败示例（真实排查日志，已脱敏，HTTP 200 + 任务失败）

```json
{
  "request_id": "a20892ba-7005-407f-82db-05857d7aee94",
  "code": null,
  "message": "",
  "output": {
    "task_id": "a7fb4fca-a4bc-42fb-aac6-85c5d8ba13aa",
    "task_status": "FAILED",
    "video_url": "",
    "code": "InvalidParameter",
    "message": "image dimensions must be between 240 and 7680 pixels"
  }
}
```

关键点：
- DashScope 任务查询常见场景是**HTTP 200**，但 `output.task_status=FAILED` 且 `output.code/output.message` 给出失败原因。
- 因此排障应同时看：HTTP 状态 + `output.task_status` + `output.code/message` + `request_id`。

---

## 4. 建议的日志落盘字段（用于后续定位）

建议每次模型调用至少记录：

```json
{
  "http_status": 200,
  "request_id": "req_xxx",
  "code": null,
  "message": "",
  "task_id": "task_xxx",
  "task_status": "PENDING|RUNNING|SUCCEEDED|FAILED",
  "output_code": "InvalidParameter",
  "output_message": "...",
  "model": "wan2.6-i2v-flash",
  "has_audio_url": true,
  "resolution": "720P",
  "duration": 10
}
```

---

## 5. 敏感信息脱敏建议

- `api_key`：仅保留前 4 位 + 后 4 位。
- `video_url` 签名参数（`Signature`/`Expires`）建议打码。
- 用户语音文案、业务用户 ID 可按内部规范匿名化。
