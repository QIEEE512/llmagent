
# 数字卡通形象（Avatar Customizer）后端接口对接文档（一期 + 二期）

> 对应前端页面：`src/pages/avatar-custom/index.vue`
>
> 对应前端网络封装：`src/services/http.js`、`src/services/api.js`

---

## 0. 总览

### 一期（已落地前端）

1. 外貌：拍照/相册选图并上传
2. 画像：年龄（8-16）+ 兴趣（多选）+ 风格 + 补充描述
3. 声线：预设库选择（不录音）
4. 生成：**同步生成**卡通形象（返回 imageUrl）
5. 本地：草稿缓存 + 生成结果保存到 `active_avatar`

### 二期（本次开始对接）

1. 声线：麦克风录音 → 上传 → 声线提取/匹配预设
2. 视频：生成 15-30 秒互动视频 → 预览（建议异步任务）

---

## 1. 基础约定

### 1.1 Base URL

- 生产环境：`https://pkhlxjidylji.sealoshzh.site/api`
- H5 本地开发：前端请求 `/api/...`，由 Vite 代理到上述域名（见 `vite.config.js`）。

### 1.2 鉴权

- 接口（除登录注册外）统一使用 Bearer Token
- Header：

```
Authorization: Bearer <access_token>
```

- 未登录/Token 过期：返回 `401`
	- 前端会在 `services/http.js` 中自动 `clearToken()`。
	- 页面会提示并跳转登录页。

### 1.3 响应结构（强约定）

前端 `services/http.js` 当前强约定：

- HTTP status 必须是 `200`
- 且业务成功必须满足：`{ ok: true }`

成功示例：
```json
{ "ok": true, "data": {} }
```

失败示例（仍然 200 也会被当成失败）：
```json
{ "ok": false, "message": "xxx" }
```

> 建议：业务失败直接用非 200（400/401/422/500），并返回 `detail` 或 `message` 字段，前端会优先展示 `detail/message`。

---

## 2. 一期接口列表

- [POST] `/avatar/upload`：上传外貌照片
- [POST] `/avatar/generate`：同步生成卡通形象

---

## 3. 上传外貌照片

### 3.1 接口

**POST** `/api/avatar/upload`

### 3.2 Content-Type

`multipart/form-data`，文件字段名：`file`

### 3.3 鉴权

需要登录：是

### 3.4 成功响应

前端会兼容字段：`data.url` / `data.fileUrl` / `data.file_url`

推荐返回：
```json
{
	"ok": true,
	"data": {
		"fileId": "img_xxx",
		"url": "/files/xxx.jpg",
		"mime": "image/jpeg",
		"width": 1024,
		"height": 1024
	}
}
```

### 3.5 失败响应（建议）

- `401` 未授权：`{ "detail": "Unauthorized" }`
- `413` 文件过大：`{ "detail": "File too large" }`
- `422` 图片不可用：`{ "detail": "Invalid portrait" }`

---

## 4. 同步生成卡通形象

### 4.1 接口

**POST** `/api/avatar/generate`

### 4.2 Content-Type

`application/json`

### 4.3 鉴权

需要登录：是

### 4.4 Request

```json
{
	"portraitUrl": "/files/xxx.jpg",
	"profile": {
		"age": 8,
		"interests": ["恐龙", "宇宙"],
		"style": "活泼",
		"freeText": "喜欢蓝色，希望有小披风"
	},
	"voice": {
		"presetId": "kid_bright_01",
		"note": "更温柔一点"
	},
	"output": {
		"characterStyle": "kids_cartoon"
	}
}
```

#### 字段说明

- `portraitUrl` (string, required)：由 `/avatar/upload` 返回的 `url`
- `profile.age` (number, required)：前端限制 3~12
- `profile.interests` (string[], optional)
- `profile.style` (string, optional)：`活泼/温柔/酷酷/搞怪/学霸`
- `profile.freeText` (string, optional，<=200)
- `voice.presetId` (string, required 一期)
	- `kid_bright_01` 活泼童声-小太阳
	- `kid_gentle_01` 温柔童声-小云朵
	- `narration_warm_01` 暖心旁白-故事时间
- `voice.note` (string, optional)
- `output.characterStyle` (string, optional)：一期固定传 `kids_cartoon`

### 4.5 Response

前端兼容：`data.imageUrl` / `data.url`，`data.avatarId` / `data.id`

推荐返回：
```json
{
	"ok": true,
	"data": {
		"avatarId": "av_123",
		"imageUrl": "/files/avatar_av_123.png",
		"meta": { "style": "kids_cartoon" }
	}
}
```

### 4.6 失败响应（建议）

- `400`：`{ "detail": "portraitUrl is required" }`
- `401`：`{ "detail": "Unauthorized" }`
- `422`：`{ "detail": "Invalid portrait or profile" }`
- `429`：`{ "detail": "Too many requests" }`
- `500`：`{ "detail": "Generation failed" }`

---

## 5. 二期：声线（录音上传 + 分析/匹配）

### 5.1 上传录音

> 你后端若已有 `/upload/voice`（项目已有 `apiUploadVoice`），建议直接复用。

**POST** `/api/upload/voice`

- Content-Type：`multipart/form-data`
- 文件字段名：`file`

成功返回（至少包含 `data.url`）：
```json
{
	"ok": true,
	"data": {
		"fileId": "voice_xxx",
		"url": "/files/voice_xxx.wav",
		"durationMs": 18300,
		"mime": "audio/wav"
	}
}
```

### 5.2 声线分析/匹配

**POST** `/api/avatar/voice/analyze`

Request：
```json
{
	"voiceUrl": "/files/voice_xxx.wav",
	"mode": "extract|match",
	"preferPresets": true
}
```

Response：
```json
{
	"ok": true,
	"data": {
		"voiceProfileId": "vp_123",
		"recommendedPresets": [
			{ "presetId": "kid_bright_01", "name": "活泼童声-小太阳", "score": 0.87 }
		]
	}
}
```

### 5.3 生成接口 voice 扩展（兼容）

当支持录音后，`/api/avatar/generate` 的 `voice` 字段可扩展：
```json
{
	"voice": {
		"voiceProfileId": "vp_123",
		"presetId": "kid_bright_01",
		"note": "更温柔一点"
	}
}
```

后端可优先使用 `voiceProfileId`；若没有则回退 `presetId`。

---

## 6. 二期：互动视频（15-30 秒）

> 强烈建议后端采用异步任务（taskId），避免长连接超时。

### 6.1 生成互动视频（建议异步）

**POST** `/api/avatar/video/generate`

Request：
```json
{
	"avatarId": "av_123",
	"durationSec": 20,
	"template": "intro|greeting|encourage",
	"script": "可选：自定义台词",
	"voice": {
		"voiceProfileId": "vp_123",
		"presetId": "kid_bright_01"
	}
}
```

Response（异步推荐）：
```json
{
	"ok": true,
	"data": { "taskId": "task_vid_789" }
}
```

### 6.2 任务查询（通用）

**GET** `/api/tasks/{taskId}`

Response：
```json
{
	"ok": true,
	"data": {
		"status": "pending|running|succeeded|failed",
		"progress": 0.35,
		"result": {
			"videoId": "vid_789",
			"videoUrl": "/files/video_vid_789.mp4",
			"coverUrl": "/files/video_vid_789.jpg",
			"durationSec": 20
		},
		"error": { "message": "..." }
	}
}
```

> 若你后端坚持同步：也可让 `/api/avatar/video/generate` 直接返回 `data.videoUrl`；前端会兼容读取。

---

## 7. 联调检查清单

- [ ] `/api/avatar/upload`：200 + `ok:true` + `data.url`
- [ ] `/api/avatar/generate`：200 + `ok:true` + `data.imageUrl`
- [ ] `/api/upload/voice`：200 + `ok:true` + `data.url`
- [ ] `/api/avatar/voice/analyze`：200 + `ok:true` + `data.voiceProfileId`（或至少 recommendedPresets）
- [ ] `/api/avatar/video/generate`：200 + `ok:true` + `data.taskId`（或同步 data.videoUrl）
- [ ] `/api/tasks/{taskId}`：200 + `ok:true`，status 正确推进直到 succeeded/failed

