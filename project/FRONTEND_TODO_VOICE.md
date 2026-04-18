# Profile Story Engine API（成长日记生成器 / 润色引擎）

本文档描述“档案页 -> 成长日记生成器”的后端对接契约。

目标：
- 前端可选择 **一个或多个会话**（conversationIds）或 **日期范围**（dateFrom/dateTo）作为素材源。
- 后端在生成故事时：
  - **包含 assistant 的解释**（即 user + assistant 消息都作为素材，按时间线编排）。
  - 自动提炼“成长里程碑”（milestones）
  - 自动生成“章节标题”（chapters[*].chapterTitle）与段落（chapters[*].paragraphs）
- 前端展示生成结果（可复制），并支持“保存到档案”（保存 story JSON）。

通用说明
- 前端所有请求需带：`Authorization: Bearer <token>`
- 返回统一结构：

```json
{
  "ok": true,
  "code": 0,
  "message": "ok",
  "data": {}
}
```

时间字段约定
- 响应中的 `createdAt` / `updatedAt` / `from` / `to` 等，均使用 ISO 8601 字符串（UTC 推荐）。

---

## 1) 生成故事

- **POST** `/api/profile/story/generate`

### Request Body

**方式 A：按会话（多选）**
```json
{
  "sourceType": "conversations",
  "conversationIds": ["c_123", "c_456"],
  "includeAssistant": true
}
```

**方式 B：按日期范围**
```json
{
  "sourceType": "dateRange",
  "dateFrom": "2026-01-01",
  "dateTo": "2026-01-31",
  "includeAssistant": true
}
```

字段说明
- `includeAssistant`: 必须支持。若为 true，后端应将 `role=user` 与 `role=assistant` 的消息都作为素材；`system` 可忽略或按需。
- Prompt 模板：**由后端决定**（前端不传 prompt）。后端可根据用户画像/配置选择模板。

### Response（200）

`data` 为 story JSON（建议稳定结构，便于前端渲染/导出）。

```json
{
  "ok": true,
  "data": {
    "storyVersion": 1,
    "title": "我的温馨成长日记",
    "chapters": [
      {
        "chapterTitle": "探索世界的小小科学家",
        "paragraphs": [
          "......",
          "......"
        ],
        "timeline": [
          {
            "at": "2026-01-28T01:25:39+08:00",
            "summary": "孩子第一次解释火山喷发原理" 
          }
        ]
      }
    ],
    "milestones": [
      {
        "title": "第一次完整拼出 cat",
        "at": "2026-01-27T09:38:15+08:00",
        "summary": "在拼读练习中，孩子把 c-a-t 连起来读对了。",
        "type": "english"
      }
    ],
    "meta": {
      "sourceType": "conversations",
      "conversationIds": ["c_123", "c_456"],
      "includeAssistant": true
    }
  }
}
```

错误码建议
- 401 未授权
- 400 参数错误（如 sourceType 不合法、dateFrom/dateTo 缺失）
- 404 素材不存在（会话不存在或不属于当前用户）

---

## 2) 保存到档案（保存 story JSON）

- **POST** `/api/profile/story/save`

### Request Body
```json
{
  "story": {
    "storyVersion": 1,
    "title": "...",
    "chapters": [],
    "milestones": [],
    "meta": {}
  },
  "source": {
    "sourceType": "conversations",
    "conversationIds": ["c_123", "c_456"],
    "includeAssistant": true
  }
}
```

### Response（200）
```json
{
  "ok": true,
  "data": {
    "storyId": "s_abcdef",
    "savedAt": "2026-02-06T10:00:00Z"
  }
}
```

实现建议
- 保存时应绑定 userId（鉴权隔离）
- 建议保存原始 `story` JSON（以便将来升级模板/导出）
- 可选：保存一份 `plainText`（用于列表预览/搜索）

---

## 3)（可选增强）已保存故事列表 / 详情

> 说明：为了让“保存到档案”可视化可管理，建议后端**正式提供** stories 列表/详情/删除。
> 前端已实现对接页面：
> - 列表：`src/pages/profile-stories/index.vue`
> - 详情：`src/pages/profile-story-detail/index.vue`

- GET `/api/profile/stories`
- GET `/api/profile/stories/{storyId}`
- POST `/api/profile/stories/{storyId}/delete`

### 3.1 列表

**GET** `/api/profile/stories`

Query（可选）
- `page`: number（默认 1）
- `pageSize`: number（默认 20，建议 <= 100）

Response（200）
```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "storyId": "s_abcdef",
        "title": "我的温馨成长日记",
        "savedAt": "2026-02-06T10:00:00Z",
        "updatedAt": "2026-02-06T10:00:00Z"
      }
    ],
    "page": 1,
    "pageSize": 20,
    "total": 1
  }
}
```

字段说明
- `items[*].title`: 用于列表展示，建议存储时冗余一份，避免每次展开 story JSON。
- `savedAt/updatedAt`: ISO 8601 字符串。

### 3.2 详情

**GET** `/api/profile/stories/{storyId}`

Response（200）
```json
{
  "ok": true,
  "data": {
    "storyId": "s_abcdef",
    "savedAt": "2026-02-06T10:00:00Z",
    "updatedAt": "2026-02-06T10:00:00Z",
    "source": {
      "sourceType": "conversations",
      "conversationIds": ["c_123", "c_456"],
      "includeAssistant": true
    },
    "story": {
      "storyVersion": 1,
      "title": "我的温馨成长日记",
      "chapters": [],
      "milestones": [],
      "meta": {}
    }
  }
}
```

### 3.3 删除

**POST** `/api/profile/stories/{storyId}/delete`

Response（200）
```json
{
  "ok": true,
  "data": {}
}
```

实现建议
- 建议软删：`deletedAt` 标记；列表默认不返回已删除。
- 鉴权：必须校验 storyId 属于当前 userId / accountId。

---

## 前端当前实现说明（对接点）

页面：`src/pages/profile-story/index.vue`

- 选择会话来源：调用 `GET /api/conversations`
- 点击生成：调用 `POST /api/profile/story/generate`
- 点击保存：调用 `POST /api/profile/story/save`

UI 约束
- 前端会尽量渲染 `chapters[*].chapterTitle` 与 `chapters[*].paragraphs`。
- 里程碑展示使用 `milestones[*].title/milestoneTitle` 与 `milestones[*].summary/desc` 等字段做兼容，但**建议后端按文档字段输出**以保持一致性。
