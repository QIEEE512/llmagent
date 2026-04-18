# 前端对接待办：图片理解（qwen3-vl-flash）

后端已支持在 `/api/chat` 中对图片附件调用千问视觉模型 `qwen3-vl-flash` 做理解，并把“图片理解结果”注入到上下文，从而生成更准确的回答。

## 1) 关键要求（必须）

为避免 SSRF 风险，后端目前 **只允许处理本服务上传后返回的 `/files/<name>` URL**。

也就是说：
- 前端上传图片必须走：`POST /api/upload/image`
- 然后把响应里的 `data.url` 原样作为 `attachments[].url` 传给 `/api/chat`

不要传第三方外链图片（例如 http(s)://xxx.com/a.png），否则后端会返回 400。

## 2) /api/chat 请求示例

```json
{
  "conversationId": "c_xxx",
  "text": "这张图里写了什么？",
  "attachments": [
    {
      "type": "image",
      "url": "https://<你的后端域名>/files/xxx.png",
      "name": "xxx.png",
      "mime": "image/png"
    }
  ]
}
```

- `text` 可以为空：当用户只发图片时，后端会用默认提示词让模型描述图片。

## 3) 当前实现边界

- 当前视觉处理为：从 `/tmp/uploads/<name>` 读取图片 → base64 → 调用 `qwen3-vl-flash`。
- 暂不支持：第三方图片 URL、需要鉴权的图片 URL、超大图（后续可加大小限制/压缩）。

如果你希望支持 OSS/CDN 外链图片，需要在后端增加“域名白名单 + 下载超时/大小限制”。
