# 前端对接待办：AI 对话附件（图片/文件）

后端已支持“上传图片/文件 + 在 /api/chat 携带 attachments”。

## 1) 上传接口

- 图片：`POST /api/upload/image`
- 文件：`POST /api/upload/file`

请求：`multipart/form-data`，字段名固定为：`file`。

响应：后端保证返回：
- `data.url`（必有）
- 并尽量返回：`data.name` / `data.size` / `data.mime`

前端建议：把这些字段缓存到待发送的附件对象中。

## 2) /api/chat 请求体

后端支持用户“只发附件不发文字”。

- 当只发附件时：`text` 可传 `""` 或不传；但 `attachments` 必须非空。
- `attachments` 每项必须包含：
  - `type`: `image` 或 `file`
  - `url`: 上传接口返回的 `data.url`
- 其他字段（可选）：`name`、`size`、`mime`

示例：
```json
{
  "conversationId": "c_xxx",
  "text": "",
  "attachments": [
    {"type": "image", "url": "https://.../a.png", "name": "a.png", "size": 123, "mime": "image/png"}
  ]
}
```

## 3) 单账号模式/新建对话

- 当前后端为单账号策略（一个用户仅一个账号），前端应隐藏“切换账户”入口。
- `/api/accounts/switch` 在单账号模式下仅作兼容保留，不应作为常规流程依赖。
- 新建对话时，请清空 conversationId 与附件缓存。

## 4) 当前后端能力边界（重要）

- 目前后端只会将附件 **作为文本描述注入模型上下文**（包含类型/文件名/URL），并写入数据库用于历史回放。
- 暂不做真实下载/解析/OCR（后续可升级到视觉理解/文件解析/知识库检索）。
