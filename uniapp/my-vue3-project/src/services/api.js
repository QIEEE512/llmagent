import { get, post, upload } from './http'

function buildQueryString(params = {}) {
	const pairs = []
	Object.entries(params || {}).forEach(([key, value]) => {
		if (value === undefined || value === null || value === '') return
		pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
	})
	return pairs.length ? `?${pairs.join('&')}` : ''
}

// Auth
export async function apiRegister(payload) {
	return post('/auth/register', payload)
}

export async function apiLogin(payload) {
	return post('/auth/login', payload)
}

// Account / User
// 获取当前登录用户信息（用于展示账号名称/账号）
export async function apiMe() {
	return get('/auth/me')
}

// 获取该用户下的账号列表（多账号管理）
export async function apiListAccounts() {
	return get('/accounts')
}

// 新增账号（创建子账号 or 绑定账号，具体由后端实现）
export async function apiCreateAccount(payload) {
	try {
		return await post('/accounts', payload)
	} catch (err) {
		if (Number(err?.status || err?.statusCode) === 409) {
			throw { ...err, message: '当前为单账号模式，不支持该操作' }
		}
		throw err
	}
}

// 删除账号
export async function apiDeleteAccount(accountId) {
	try {
		return await post(`/accounts/${accountId}/delete`)
	} catch (err) {
		if (Number(err?.status || err?.statusCode) === 409) {
			throw { ...err, message: '当前为单账号模式，不支持该操作' }
		}
		throw err
	}
}

// 切换当前账号（如果后端需要一个 activeAccount 概念）
export async function apiSwitchAccount(accountId) {
	try {
		return await post('/accounts/switch', { accountId })
	} catch (err) {
		if (Number(err?.status || err?.statusCode) === 409) {
			throw { ...err, message: '当前为单账号模式，不支持该操作' }
		}
		throw err
	}
}

// Chat
export async function apiGetRecommendations() {
	return get('/recommendations')
}

export async function apiChat(payload) {
	// chat 推理可能较慢：建议超时 >= 20s（这里设为 60s）
	return post('/chat', payload, { timeout: 60000 })
}

// Upload
export async function apiUploadChatImage(filePath) {
	return upload({ path: '/upload/image', filePath, name: 'file' })
}

export async function apiUploadChatFile(filePath) {
	return upload({ path: '/upload/file', filePath, name: 'file' })
}

// Doc interpret (AI 文档解读)
// 说明：上传先走通 /upload/file；解读接口由后端提供（见对接文档）
export async function apiUploadDocument(filePath) {
	return upload({ path: '/upload/file', filePath, name: 'file' })
}

export async function apiDocInterpret(payload) {
	// 预留：后端实现后即可联调
	// payload: { fileUrl, fileName?, fileSize?, fileMime?, question?, conversationId? }
	return post('/doc/interpret', payload, { timeout: 60000 })
}

export async function apiUploadAvatarImage(filePath) {
	return upload({ path: '/avatar/upload', filePath, name: 'file' })
}

// ASR
export async function apiAsr(payload) {
	return post('/asr', payload)
}

// Voice
// 上传录音文件（multipart/form-data, field name = file）
export async function apiUploadVoice(filePath) {
	// 录音文件一般较大，给更长超时
	return upload({ path: '/upload/voice', filePath, name: 'file', timeout: 60000 })
}

// Voice analyze / match presets
// payload: { voiceUrl, mode: 'extract'|'match', preferPresets?: boolean }
export async function apiVoiceAnalyze(payload) {
	return post('/avatar/voice/analyze', payload, { timeout: 60000 })
}

// 语音理解（qwen 语音模型）：上传后用 voiceUrl 发起对话
export async function apiVoiceChat(payload) {
	// payload: { voiceUrl, conversationId?, meta? }
	return post('/voice/chat', payload, { timeout: 60000 })
}

// Video generate (recommended async taskId)
// payload: { avatarId, durationSec, template, script?, voice? }
export async function apiAvatarVideoGenerate(payload, scope = 'user') {
	const qs = scope ? `?scope=${encodeURIComponent(scope)}` : ''
	return post(`/avatar/video/generate${qs}`, payload, { timeout: 60000 })
}

// Video generate (new minimal contract)
// POST /api/avatar/video/generate
// body: { imageUrl: "/files/xxx.png", prompt?: "..." }
// resp: { ok:true, data: { jobId } }
export async function apiAvatarVideoGenerateByImage(payload, scope = 'user') {
	const qs = scope ? `?scope=${encodeURIComponent(scope)}` : ''
	return post(`/avatar/video/generate${qs}`, payload, { timeout: 60000 })
}

// Video status (new minimal contract)
// GET /api/avatar/video/status?jobId=...
// resp: { ok:true, data: { jobId, status, videoUrl } }
export async function apiAvatarVideoStatus(jobId, scope = 'user') {
	const qs = scope ? `&scope=${encodeURIComponent(scope)}` : ''
	return get(`/avatar/video/status?jobId=${encodeURIComponent(jobId)}${qs}`)
}

// Generic task query
export async function apiGetTask(taskId) {
	return get(`/tasks/${taskId}`)
}

// Avatar generate
export async function apiAvatarGenerate(payload, scope = 'user') {
	// 生成通常较慢：单独给更长超时（90s~180s），避免使用全局默认
	const qs = scope ? `?scope=${encodeURIComponent(scope)}` : ''
	return post(`/avatar/generate${qs}`, payload, { timeout: 120000 })
}

// 获取当前激活头像（支持 scope=user|account）
export async function apiGetActiveAvatar(scope = 'user') {
	const qs = scope ? `?scope=${encodeURIComponent(scope)}` : ''
	return get(`/avatar/active${qs}`)
}

// Conversations (历史对话管理)
// GET /api/conversations -> { ok:true, data: [ { conversationId, title, lastMessage, updatedAt } ] }
export async function apiGetConversations() {
	return get('/conversations')
}

// POST /api/conversations -> { ok:true, data: { conversationId, title } }
export async function apiCreateNewConversation(payload = {}) {
	// payload 可为空或 { title? }
	return post('/conversations', payload)
}

// GET /api/conversations/:id -> { ok:true, data: { conversationId, messages: [...] } }
export async function apiGetConversation(id) {
	return get(`/conversations/${encodeURIComponent(id)}`)
}

// POST /api/conversations/:id/messages -> append a message to a conversation
// body: { role, text, attachments?, clientMsgId? }
// resp: { ok:true, data: { messageId } }
export async function apiAppendConversationMessage(id, payload) {
	return post(`/conversations/${encodeURIComponent(id)}/messages`, payload)
}

// DELETE /api/conversations/:id -> { ok:true }
export async function apiDeleteConversation(id) {
	return post(`/conversations/${encodeURIComponent(id)}/delete`)
}

// Profile Story Engine（成长档案生成器）
// POST /api/profile/story/generate -> { ok:true, data: storyJson }
// body: { sourceType: 'conversations'|'dateRange', conversationIds?, dateFrom?, dateTo?, includeAssistant: true }
export async function apiGenerateProfileStory(payload) {
	return post('/profile/story/generate', payload, { timeout: 120000 })
}

// Profile Story Extract (upload material -> AI polish & extract -> storyJson)
// POST /api/profile/story/extract
// body: { profile?: { name, learningGoal, preferences }, rawText?: string, fileUrl?: string }
// resp: { ok:true, data: storyJson }
export async function apiExtractProfileStoryFromMaterial(payload) {
	return post('/profile/story/extract', payload, { timeout: 120000 })
}

// POST /api/profile/story/save -> { ok:true, data: { storyId } }
// body: { story: <storyJson>, source: { ... } }
export async function apiSaveProfileStory(payload) {
	return post('/profile/story/save', payload, { timeout: 60000 })
}

// Profile Story Update (edit story/profile fields)
// POST /api/profile/stories/:storyId/update
// body: { story?: storyJson, profile?: { name, learningGoal, preferences } }
// resp: { ok:true, data: { updatedAt } }
export async function apiUpdateProfileStory(storyId, payload) {
	return post(`/profile/stories/${encodeURIComponent(storyId)}/update`, payload, { timeout: 60000 })
}

// Profile Stories（已保存的成长档案）
// GET /api/profile/stories -> { ok:true, data: { items: [ { storyId, title, savedAt, updatedAt? } ] } }
// query: ?page=1&pageSize=20 (optional)
export async function apiListProfileStories(params = {}) {
	const suffix = buildQueryString(params)
	try {
		return await get(`/profile/stories${suffix}`)
	} catch (err) {
		// 兼容旧路径：/profile/story/list
		return get(`/profile/story/list${suffix}`)
	}
}

// GET /api/profile/stories/:storyId -> { ok:true, data: { storyId, story, source, savedAt, updatedAt } }
export async function apiGetProfileStory(storyId) {
	const sid = encodeURIComponent(storyId)
	try {
		return await get(`/profile/stories/${sid}`)
	} catch (err) {
		// 兼容旧路径：/profile/story/detail/:storyId
		return get(`/profile/story/detail/${sid}`)
	}
}

// POST /api/profile/stories/:storyId/delete -> { ok:true, data: {} }
export async function apiDeleteProfileStory(storyId) {
	return post(`/profile/stories/${encodeURIComponent(storyId)}/delete`)
}

// Profile Story Share（导出/分享/撤销）
// POST /api/profile/stories/:storyId/export-word -> { ok:true, data: { exportId, fileUrl, pdfUrl } }
export async function apiExportProfileStoryWord(storyId) {
	return post(`/profile/stories/${encodeURIComponent(storyId)}/export-word`, {}, { timeout: 120000 })
}

// POST /api/profile/stories/:storyId/share -> { ok:true, data: { shareId, shareUrl, shareFullUrl?, expiresAt, status } }
// Frontend strategy: prefer data.shareFullUrl if provided; else build full url using <public api origin> + shareUrl
export async function apiCreateProfileStoryShare(storyId, payload) {
	return post(`/profile/stories/${encodeURIComponent(storyId)}/share`, payload || {}, { timeout: 60000 })
}

// POST /api/profile/shares/:shareId/revoke -> { ok:true, data: { status: 'revoked', revokedAt } }
export async function apiRevokeProfileShare(shareId) {
	return post(`/profile/shares/${encodeURIComponent(shareId)}/revoke`, {}, { timeout: 60000 })
}
