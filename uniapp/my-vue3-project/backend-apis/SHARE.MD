# 档案分享（Profile Story Share）前端对接文档（MVP）

> 适用日期：2026-02-07

本文档覆盖 MVP 必需的 4 个接口：导出 Word（快照）、创建分享、撤销分享、公开下载入口。

## 通用约定

- 所有 `/api/**` 接口需要登录（`Authorization: Bearer <token>`）。
- `ApiResponse` 结构：`{ ok: true, code: 0, message: "ok", data: ... }`
- 错误返回使用 HTTP status code + `detail`（FastAPI 默认）。

## 数据名词

- `storyId`: 已保存的成长档案（profile story）ID，如 `s_xxx`
- `exportId`: 导出快照 ID（每次导出生成新的快照），如 `e_xxx`
- `shareId`: 分享 ID（不可枚举随机 token），如 `Sh_xxx`

---

## 1) 导出 Word（生成快照）

### POST `/api/profile/stories/{storyId}/export-word`

**鉴权**：需要登录；仅 story 拥有者可导出。

#### Request Body（可选）

```json
{ "template": "default" }
```

#### Response（200）

```json
{
  "ok": true,
  "data": {
    "exportId": "e_abcdef",
    "storyId": "s_123",
    "fileName": "成长档案_2026-02-07_我的温馨成长日记.docx",
    "fileUrl": "https://...", 
    "createdAt": "2026-02-07T10:00:00Z"
  }
}
```

- `fileUrl`：后端生成的 **短期** OSS 签名下载链接（用于立即下载/预览）。

#### 常见错误

- `401`：未登录
- `404`：story 不存在或无权限
- `503`：OSS 或 DB 不可用

---

## 2) 创建分享（默认 7 天有效）

### POST `/api/profile/stories/{storyId}/share`

**鉴权**：需要登录；仅 story 拥有者可创建分享。

#### Request Body（推荐）

```json
{ "exportId": "e_abcdef", "expiresInDays": 7 }
```

说明：
- `exportId` 可选：
  - 传了：绑定指定快照
  - 不传：后端会取最新快照；若没有快照则自动先导出一个
- `expiresInDays` 可选，默认 7；后端会限制到 1~30。

#### Response（200）

```json
{
  "ok": true,
  "data": {
    "shareId": "Sh_xxx",
    "shareUrl": "/s/Sh_xxx",
    "expiresAt": "2026-02-14T10:00:00Z",
    "status": "active"
  }
}
```

前端拼接完整 URL：
- `shareFullUrl = <后端域名> + shareUrl`

#### 常见错误

- `401`：未登录
- `404`：story 不存在或无权限 / exportId 不存在或不属于该 story
- `503`：OSS 或 DB 不可用

---

## 3) 一键取消分享

### POST `/api/profile/shares/{shareId}/revoke`

**鉴权**：需要登录；仅创建者可撤销。

#### Response（200）

```json
{
  "ok": true,
  "data": {
    "shareId": "Sh_xxx",
    "status": "revoked",
    "revokedAt": "2026-02-07T10:30:00Z"
  }
}
```

说明：
- 接口是幂等的：重复撤销会继续返回 `revoked`。

#### 常见错误

- `401`：未登录
- `404`：share 不存在或不属于当前用户

---

## 4) 公开下载入口（无需登录）

### GET `/s/{shareId}`

**鉴权**：无需登录。

#### 行为

- shareId 不存在：`404`
- 已撤销：`410`
- 已过期：`410`
- 有效：返回 `302`，`Location` 指向 OSS **短期** signed url（默认约 10 分钟）。

前端建议：
- 直接 `window.location.href = shareFullUrl` 即可触发下载。
- 或 `<a href={shareFullUrl} target="_blank" rel="noreferrer">下载</a>`。

---

## 前端落地建议（最小）

- 保存 story 后拿到 `storyId`
- 用户点击“导出 Word”
  - 调用 export 接口，拿到 `exportId`（可立即用 `fileUrl` 下载）
- 用户点击“分享”
  - 调用 share 接口，拿到 `shareUrl`，复制完整链接给他人
- 用户点击“撤销分享”
  - 调用 revoke 接口

