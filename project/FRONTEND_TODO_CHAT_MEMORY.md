# Conversations API （历史对话 / ChatGPT 式会话存储）

描述前端实现“像 ChatGPT Web 一样”的对话历史所需要的后端契约：
- 列出会话（用于历史页左侧列表）
- 创建新会话
- 读取单个会话（含消息）
- 追加消息（用户/assistant 都要落库，用于历史列表 lastMessage/updatedAt）
- 删除会话（软删）

通用说明
- 前端所有请求需带 Authorization: Bearer <token>
- 返回统一结构：

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": ...
}
```

API 列表

1) 列出会话
- GET /api/conversations
- Request: 无
- Response: 200
```
{
  "ok": true,
  "data": [
    {
      "conversationId": "c_123",
      "title": "关于作业的问题",
      "lastMessage": "上次聊天的最后一条摘要",
      "updatedAt": "2026-01-29T12:34:56Z"
    }
  ]
}
```

2) 创建新会话
- POST /api/conversations
- Request body (可选): { title?: string }
- Response: 200
```
{
  "ok": true,
  "data": {
    "conversationId": "c_456",
    "title": "新对话"
  }
}
```

3) 获取单个会话（含消息）
- GET /api/conversations/{conversationId}
- Response: 200
```
{
  "ok": true,
  "data": {
    "conversationId": "c_456",
    "title": "新对话",
    "messages": [
      {
        "messageId": "m1",
        "role": "user|assistant|system",
        "text": "...",
        "attachments": [
          { "type": "image|file", "url": "/files/xxx.png", "name": "...", "size": 123, "mime": "..." }
        ],
        "createdAt": "2026-01-29T12:34:56Z"
      }
    ]
  }
}
```

4) 追加消息（会话落库的关键接口）
- POST /api/conversations/{conversationId}/messages
- 说明：
  - 前端在“发送消息”时，会先追加一条 user 消息（用于历史列表 lastMessage 即时更新），然后再调用 /api/chat 或其它推理接口拿到回复后，再追加一条 assistant 消息。
  - 若后端的 /api/chat 已经做了落库，也可以让该接口成为可选；但为了便于解耦（推理服务不一定落库），建议保留该接口。

- Request body:
```json
{
  "role": "user",
  "text": "你好",
  "attachments": [
    { "type": "image", "url": "/files/a.png", "name": "图片", "size": 12345, "mime": "image/png" }
  ],
  "clientMsgId": "u-1700000000000"
}
```

- Response: 200
```json
{
  "ok": true,
  "data": {
    "messageId": "m_789",
    "conversationId": "c_456",
    "updatedAt": "2026-01-29T12:35:12Z"
  }
}
```

5) 删除会话（软删）
- POST /api/conversations/{conversationId}/delete
- Response: 200
```
{ "ok": true }
```

实现建议
- 会话列表按 `updatedAt` 降序返回
- 创建时若未提供 `title`，后端可基于第一条用户消息自动生成或使用 `"新对话"`
- 删除采用软删除并保留 `conversationId` 可恢复
- 若支持分页，可在 `GET /api/conversations` 支持 `?page=&limit=`

后端需要做的工作（对接要点）
1) 存储结构
- conversations 表/集合：
  - id(conversationId), userId, title, createdAt, updatedAt, deletedAt?
  - lastMessage（可冗余字段，加速列表）
- messages 表/集合：
  - id(messageId), conversationId, role, text, attachments(json), createdAt
  - clientMsgId（可选，用于幂等去重：前端网络重试时避免重复写入）

2) 鉴权与隔离
- 所有接口必须按 token 对 userId 进行隔离：用户只能访问自己的会话。

3) 列表字段维护
- 当追加消息时：
  - conversations.updatedAt 必须更新
  - conversations.lastMessage 建议更新为该消息的简短摘要（如 text 前 50 字，或附件摘要）

4) 幂等（强烈建议）
- `POST /conversations/{id}/messages` 建议支持幂等：
  - 若 clientMsgId 已存在（同一 conversationId + clientMsgId），返回已有 messageId；避免前端重试造成重复消息。

5) 与 /api/chat 的关系
- 如果 /api/chat 本身会落库：它可以在响应中返回 conversationId/messageId；但历史页仍然建议依赖本文件中的 conversations 接口来展示。
- 如果 /api/chat 不落库：前端会走“追加 user 消息 -> 调用 /api/chat -> 追加 assistant 消息”的流程（当前前端已按此实现）。

错误码
- 401: 未授权
- 404: 会话不存在
- 400: 参数错误

