# 微信式「按下开始、松开停止」语音输入：后端需要完成/调整的工作清单

日期：2026-01-26

本文对应前端实现位置：`src/pages/chat/index.vue`（聊天页底部输入栏）。

## 目标

前端已实现微信式语音交互：

- 点击右侧话筒按钮切换到语音模式
- **按下**“按住说话”按钮开始录音
- **松开**按钮停止录音
- 松开后弹出确认框：取消/发送
- 发送会走现有链路：`/api/upload/voice` → `/api/voice/chat`，并把返回文本填入输入框

后端需要保证：

1) 能可靠接收并保存前端上传的音频文件（aac 为主）。
2) 能根据上传后返回的 `voiceUrl` 做语音理解/转写并返回文本。

## 已约定与当前前端调用（请对齐）

### 1) 上传语音文件

- 方法：`POST /api/upload/voice`
- Content-Type：`multipart/form-data`
- 字段名：`file`
- 前端超时：60s

#### 返回格式（统一 ApiResponse）

建议返回：

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "url": "/files/voice/xxx.aac",
    "name": "xxx.aac",
    "size": 12345,
    "mime": "audio/aac"
  }
}
```

约束：

- `data.url` 必须是可被后续接口访问的 URL（建议是站内 `/files/...`）
- 允许前端上传的 `filePath` 在 App 端为本地路径（如 `_doc/...`），由 `multipart` 读取文件；因此后端只需处理标准上传即可。

### 2) 语音理解/语音转文本（对话）

- 方法：`POST /api/voice/chat`
- Content-Type：`application/json`

请求体：

```json
{
  "voiceUrl": "/files/voice/xxx.aac",
  "conversationId": "可选-用于多轮",
  "meta": { "source": "voice" }
}
```

返回体（前端兼容字段）：

- 推荐：

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {
    "text": "识别/理解后的文本",
    "conversationId": "可选"
  }
}
```

- 前端也兼容：`{ data: { answer: "..." } }` 或 `{ text: "..." }` / `{ answer: "..." }`。

## 后端需要实现/改动点

### A. 上传接口：校验、存储与可访问 URL

必须实现：

- 支持音频类型（尤其 `audio/aac`，也可能出现 `audio/mp4`、`audio/m4a` 等，建议白名单更宽一点）
- 文件大小限制：建议 >= 10MB（15~60s 的 aac 常见在几百 KB 到数 MB）
- 存储到：`/files/voice/` 或类似目录
- 返回稳定的 `data.url`

建议实现：

- 通过 magic bytes / MIME 嗅探做二次校验，避免仅凭扩展名
- 统一错误返回：`{ ok:false, code:xxxx, message:"..." }`，便于前端 toast

### B. voiceUrl 可被后端访问

后端在处理 `/api/voice/chat` 时，需要能拿到 `voiceUrl` 对应的音频文件内容。

两种方式任选其一（建议 1）：

1. **本地文件直读（推荐）**
   - 若 `voiceUrl` 是站内 `/files/...`，可映射到本地磁盘路径并直接读取。
2. HTTP 拉取
   - 如果 `voiceUrl` 是完整 URL，后端可发起 HTTP GET 拉取，再送给模型。

### C. 语音模型能力（理解/转写）

必须实现：

- 输入：音频文件（二进制）
- 输出：可用于聊天的文本（`text` 或 `answer`）

建议实现：

- 保留原始转写文本 + 可选“意图理解后组织的文本”字段
- 记录 `conversationId`，与 `/api/chat` 共用记忆

### D. 错误与边界情况（前端期望）

前端交互是“按下开始、松开停止”，容易出现：

- 录音太短（< 300ms~1s）：建议后端返回明确错误码/提示，如“录音时间太短”
- 音频格式不支持：返回明确提示
- 模型处理超时：建议后端超时 >= 60s，并返回可读 message（前端会 toast）

### E. 不需要你改动的部分（当前方案）

- **不需要新增**“分片上传/流式识别”接口：当前是录完一次性上传
- **不需要改动**前端现有 `/api/upload/voice` 和 `/api/voice/chat` 路径（只要按本文实现即可）

## 可选增强（后续想更像微信）

如果你希望体验更接近微信（实时“上滑取消发送”等），后端可以考虑：

- 增加 `/api/voice/asr`：只做转写，返回纯文本（更快），前端再把文本塞给 `/api/chat`
- 增加对 opus/pcm 的支持（某些端录音格式可能变动）

---

如需我把这份文档同步链接到你项目已有的 `backend-apis/*.md` 目录结构里（比如统一命名、引用 README），我也可以顺手整理一版索引。
