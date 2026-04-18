<template>
	<view class="page">
		<view class="card">
			<view class="card-title">成长档案记录</view>
			<view class="card-sub">从历史对话中生成你的成长故事</view>
		</view>

		<view class="card">
			<view class="section-title">选择素材</view>

			<view class="mode-row">
				<view class="mode" :class="{ active: sourceMode === 'conversations' }" @tap="sourceMode = 'conversations'">按会话</view>
				<view class="mode" :class="{ active: sourceMode === 'upload' }" @tap="sourceMode = 'upload'">上传资料</view>
			</view>

			<!-- 按会话：多选会话 -->
			<view v-if="sourceMode === 'conversations'" class="block">
				<view class="hint">点击选择一个或多个会话（可多选）</view>
				<view v-if="loading.conversations" class="muted">正在加载会话列表…</view>
				<view v-else>
					<view v-if="!conversations.length" class="muted">暂无会话，请先去聊天页产生对话</view>
					<view v-else class="list">
						<view
							v-for="c in conversations"
							:key="c.conversationId"
							class="item"
							:class="{ selected: selectedConversationIds.includes(c.conversationId) }"
							@click="toggleConversation(c.conversationId)"
						>
							<view class="item-hd">
								<view class="item-title">{{ c.title || '新对话' }}</view>
								<view class="badge" v-if="selectedConversationIds.includes(c.conversationId)">已选</view>
							</view>
							<view class="item-sub">{{ c.lastMessage || '' }}</view>
							<view class="item-time">{{ formatDate(c.updatedAt) }}</view>
						</view>
					</view>
				</view>
			</view>

			<!-- 上传资料：文本 + 可选文件 -->
			<view v-else-if="sourceMode === 'upload'" class="block">
				<view class="hint">粘贴或上传一份“成长档案原始信息”（例如简历/获奖记录/学习情况），AI 会润色并提取为当前档案格式。</view>
				<view class="field" style="padding: 8px 0 2px;">
					<u-input
						v-model="rawText"
						type="textarea"
						autoHeight
						:maxlength="4000"
						:showConfirmBar="false"
						placeholder="在此粘贴原始资料（推荐）"
						border="none"
						:customStyle="textareaStyle"
					/>
				</view>
				<view class="upload-row">
					<u-button type="default" shape="circle" :customStyle="ghostBtnStyle" :loading="loading.upload" @tap="pickAndUploadFile">选择并上传文件</u-button>
					<view class="muted" v-if="uploadedFile.fileUrl">已上传：{{ uploadedFile.fileName || uploadedFile.fileUrl }}</view>
					<view class="muted" v-else>可选：上传 doc/pdf/txt/图片（以你后端支持为准）</view>
				</view>
			</view>

			<view class="actions">
				<u-button
					type="primary"
					shape="circle"
					:customStyle="primaryBtnStyle"
					:loading="loading.generate"
					:disabled="!canGenerate"
					@tap="generateStory"
				>生成档案</u-button>
			</view>
			<view v-if="loading.generate" class="generating">正在生成档案，请稍候…</view>
		</view>

		<!-- 生成结果展示 -->
		<view v-if="story" class="card">
			<view class="card-hd">
				<view class="result-title-row">
					<view class="card-title">生成结果</view>
					<view v-if="storyMeta.degraded" class="quality-badge">简版</view>
				</view>
				<u-button type="default" shape="circle" :customStyle="editBtnStyle" @tap="toggleStoryProfileEdit">{{ isEditingStoryProfile ? '保存' : '编辑' }}</u-button>
			</view>

			<view v-if="storyMeta.degraded" class="warn">已生成简版档案（模型超时自动降级）</view>
			<view v-if="storyMeta.materialTruncated" class="warn">素材过长已截断，结果可能偏摘要</view>

			<view class="field" style="padding-top: 6px;">
				<view class="label">姓名</view>
				<view v-if="!isEditingStoryProfile" class="value-text">{{ displayText(storyProfile.name) }}</view>
				<u-input v-else v-model="storyProfile.name" placeholder="例如：小明" border="none" :customStyle="inputStyle" />
			</view>
			<view class="field">
				<view class="label">学习目标</view>
				<view v-if="!isEditingStoryProfile" class="value-text">{{ displayText(storyProfile.learningGoal) }}</view>
				<u-input v-else v-model="storyProfile.learningGoal" placeholder="例如：每天进步一点点" border="none" :customStyle="inputStyle" />
			</view>
			<view class="field">
				<view class="label">学习偏好</view>
				<view v-if="!isEditingStoryProfile" class="value-text value-text-multi">{{ displayText(storyProfile.preferences) }}</view>
				<u-input v-else v-model="storyProfile.preferences" type="textarea" autoHeight :maxlength="200" :showConfirmBar="false" placeholder="例如：科学、语文、英语" border="none" :customStyle="textareaStyle" />
			</view>

			<view class="story-title" v-if="story.title">{{ story.title }}</view>

			<view class="copy-row">
				<u-button type="default" shape="circle" :customStyle="ghostBtnStyle" @tap="copyAll">复制全文</u-button>
				<u-button type="primary" shape="circle" :customStyle="ghostPrimaryBtnStyle" :loading="loading.save" @tap="saveToProfile">保存到档案</u-button>
				<u-button type="default" shape="circle" :customStyle="ghostBtnStyle" :loading="loading.generate" @tap="regenerateHighQuality">重新生成（高质量）</u-button>
			</view>

			<view v-if="Array.isArray(story.chapters) && story.chapters.length" class="chapters">
				<view v-for="(ch, idx) in story.chapters" :key="idx" class="chapter">
					<view class="chapter-title">{{ ch.chapterTitle || `第${idx + 1}章` }}</view>
					<view v-if="Array.isArray(ch.paragraphs)" class="paras">
						<view v-for="(p, pi) in ch.paragraphs" :key="pi" class="para">{{ p }}</view>
					</view>
				</view>
			</view>
			<view v-else class="muted">后端未返回 chapters，仍可通过“复制全文”拿到内容</view>

			<view v-if="Array.isArray(story.milestones) && story.milestones.length" class="miles">
				<view class="section-sub">成长里程碑</view>
				<view v-for="(m, mi) in story.milestones" :key="mi" class="milestone">
					<view class="milestone-title">{{ m.title || m.milestoneTitle || '里程碑' }}</view>
					<view class="milestone-sub">{{ m.time || m.date || m.at || '' }} {{ m.summary || m.desc || '' }}</view>
				</view>
			</view>
		</view>

	</view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiGetConversations, apiGenerateProfileStory, apiSaveProfileStory, apiUploadDocument, apiExtractProfileStoryFromMaterial } from '@/services/api'
import { getUserProfile } from '@/services/userProfile'

const sourceMode = ref('conversations') // 'conversations' | 'upload'
const conversations = ref([])
const selectedConversationIds = ref([])
const story = ref(null)

const profileForm = reactive({ name: '', learningGoal: '', preferences: '' })
const storyProfile = reactive({ name: '', learningGoal: '', preferences: '' })

const isEditingStoryProfile = ref(false)

const rawText = ref('')
const uploadedFile = reactive({ fileUrl: '', fileName: '' })

const loading = ref({
	conversations: false,
	generate: false,
	save: false,
	upload: false,
})

const storyMeta = computed(() => {
	const meta = story.value?.meta || {}
	return {
		degraded: !!meta?.degraded,
		materialTruncated: !!meta?.material?.truncated,
	}
})

function isYMD(value) {
	return /^\d{4}-\d{2}-\d{2}$/.test(String(value || '').trim())
}


const canGenerate = computed(() => {
	if (loading.value.generate) return false
	if (sourceMode.value === 'conversations') return selectedConversationIds.value.length > 0
	if (sourceMode.value === 'upload') return !!rawText.value.trim() || !!uploadedFile.fileUrl
	return false
})

onShow(() => {
	try {
		Object.assign(profileForm, getUserProfile())
	} catch (e) {
		// ignore
	}
	fetchConversations()
})

function displayText(v) {
	const s = String(v || '').trim()
	return s ? s : '未填写'
}

function saveStoryProfileEdits() {
	storyProfile.name = String(storyProfile.name || '').trim()
	storyProfile.learningGoal = String(storyProfile.learningGoal || '').trim()
	storyProfile.preferences = String(storyProfile.preferences || '').trim()
	if (story.value) story.value.profile = { ...storyProfile }
}

function toggleStoryProfileEdit() {
	if (isEditingStoryProfile.value) {
		saveStoryProfileEdits()
		isEditingStoryProfile.value = false
		return
	}
	isEditingStoryProfile.value = true
}

async function fetchConversations() {
	loading.value.conversations = true
	try {
		const res = await apiGetConversations()
		conversations.value = Array.isArray(res?.data) ? res.data : []
	} catch (e) {
		console.error('fetch conversations error', e)
		conversations.value = []
	} finally {
		loading.value.conversations = false
	}
}

function toggleConversation(id) {
	const idx = selectedConversationIds.value.indexOf(id)
	if (idx >= 0) selectedConversationIds.value.splice(idx, 1)
	else selectedConversationIds.value.push(id)
}

async function generateStory() {
	if (sourceMode.value === 'conversations' && !selectedConversationIds.value.length) {
		uni.showToast({ title: '请至少选择一个会话', icon: 'none' })
		return
	}

	loading.value.generate = true
	try {
		story.value = null
		const baseProfile = {
			name: String(profileForm.name || '').trim(),
			learningGoal: String(profileForm.learningGoal || '').trim(),
			preferences: String(profileForm.preferences || '').trim(),
		}
		let res
		if (sourceMode.value === 'upload') {
			res = await apiExtractProfileStoryFromMaterial({
				profile: baseProfile,
				rawText: String(rawText.value || '').trim(),
				fileUrl: uploadedFile.fileUrl || '',
			})
		} else {
			const payload = {
				sourceType: 'conversations',
				conversationIds: [...selectedConversationIds.value],
				includeAssistant: true,
				profile: baseProfile,
			}
			res = await apiGenerateProfileStory(payload)
		}

		story.value = res?.data || null
		if (!story.value) {
			uni.showToast({ title: '生成失败：无返回数据', icon: 'none' })
			return
		}

		// 确保生成档案里带上这些可编辑信息（即使后端不回传也能在前端保存）
		Object.assign(storyProfile, {
			name: story.value?.profile?.name || baseProfile.name,
			learningGoal: story.value?.profile?.learningGoal || baseProfile.learningGoal,
			preferences: story.value?.profile?.preferences || baseProfile.preferences,
		})
		story.value.profile = { ...storyProfile }

		if (storyMeta.value.degraded) {
			uni.showToast({ title: '已生成简版档案（模型超时自动降级）', icon: 'none', duration: 2600 })
		}
		if (storyMeta.value.materialTruncated) {
			uni.showToast({ title: '素材过长已截断，结果可能偏摘要', icon: 'none', duration: 2600 })
		}
	} catch (e) {
		console.error('generate story error', e)
		const status = Number(e?.status || e?.statusCode)
		if (status === 504) {
			uni.showToast({ title: '模型超时，可重试/稍后再试', icon: 'none' })
		} else if (status === 502) {
			uni.showToast({ title: '模型返回异常', icon: 'none' })
		} else if (status === 404) {
			uni.showToast({ title: '暂无可用素材', icon: 'none' })
		} else if (status === 400) {
			uni.showToast({ title: '参数错误（请检查日期/会话）', icon: 'none' })
		} else {
			uni.showToast({ title: '生成失败', icon: 'none' })
		}
	} finally {
		loading.value.generate = false
	}
}

function regenerateHighQuality() {
	return generateStory()
}

function buildTextForCopy(s) {
	if (!s) return ''
	const lines = []
	const p = s.profile || {}
	if (p.name) lines.push(`姓名：${String(p.name)}`)
	if (p.learningGoal) lines.push(`学习目标：${String(p.learningGoal)}`)
	if (p.preferences) lines.push(`学习偏好：${String(p.preferences)}`)
	if (s.title) lines.push(String(s.title))
	if (Array.isArray(s.chapters)) {
		s.chapters.forEach((ch, i) => {
			lines.push('')
			lines.push(String(ch.chapterTitle || `第${i + 1}章`))
			if (Array.isArray(ch.paragraphs)) ch.paragraphs.forEach(p => lines.push(String(p)))
		})
	}
	if (Array.isArray(s.milestones) && s.milestones.length) {
		lines.push('')
		lines.push('成长里程碑')
		s.milestones.forEach(m => {
			const t = m.title || m.milestoneTitle || '里程碑'
			const time = m.time || m.date || m.at || ''
			const sum = m.summary || m.desc || ''
			lines.push(`- ${t}${time ? `（${time}）` : ''}${sum ? `：${sum}` : ''}`)
		})
	}
	return lines.join('\n')
}

function copyAll() {
	const text = buildTextForCopy(story.value)
	if (!text) return uni.showToast({ title: '暂无可复制内容', icon: 'none' })
	uni.setClipboardData({ data: text })
}

async function saveToProfile() {
	if (!story.value) return
	loading.value.save = true
	try {
		// 保存前把可编辑信息写回 story
		story.value.profile = {
			name: String(storyProfile.name || '').trim(),
			learningGoal: String(storyProfile.learningGoal || '').trim(),
			preferences: String(storyProfile.preferences || '').trim(),
		}

		const source = sourceMode.value === 'conversations'
			? { sourceType: 'conversations', conversationIds: selectedConversationIds.value }
			: { sourceType: 'upload', rawText: String(rawText.value || '').trim(), fileUrl: uploadedFile.fileUrl || '' }

		const res = await apiSaveProfileStory({ story: story.value, source })
		const storyId = res?.data?.storyId || ''
		uni.showModal({
			title: '已保存到档案',
			content: storyId ? '已保存成功，是否去查看已保存档案？' : '已保存成功，是否去查看已保存档案？',
			confirmText: '去查看',
			cancelText: '继续',
			success: (r) => {
				if (!r.confirm) return
				uni.navigateTo({ url: '/pages/profile-stories/index' })
			},
		})
	} catch (e) {
		console.error('save story error', e)
		uni.showToast({ title: '保存失败', icon: 'none' })
	} finally {
		loading.value.save = false
	}
}

async function pickAndUploadFile() {
	loading.value.upload = true
	try {
		// 以“上传后端文件服务(/upload/file)”为前置，然后把 fileUrl 交给 AI 提取接口
		const filePath = await pickLocalFilePath()
		if (!filePath) {
			uni.showToast({ title: '当前平台不支持文件选择，请使用系统文件选择器', icon: 'none' })
			return
		}
		const up = await apiUploadDocument(filePath)
		uploadedFile.fileUrl = up?.data?.url || up?.data?.fileUrl || ''
		uploadedFile.fileName = up?.data?.name || ''
		if (!uploadedFile.fileUrl) {
			uni.showToast({ title: '上传成功但未返回 fileUrl', icon: 'none' })
		}
	} catch (e) {
		console.error('upload material error', e)
		uni.showToast({ title: e?.message || '上传失败', icon: 'none' })
	} finally {
		loading.value.upload = false
	}
}

function pickLocalFilePath() {
	return new Promise((resolve) => {
		// 仅文件选择：chooseMessageFile(小程序) -> chooseFile(H5/部分端) -> plus.io.chooseFile(App)
		try {
			if (typeof uni.chooseMessageFile === 'function') {
				uni.chooseMessageFile({
					count: 1,
					type: 'file',
					success: (r) => {
						const p = r?.tempFiles?.[0]?.path || r?.tempFiles?.[0]?.tempFilePath || ''
						resolve(p)
					},
					fail: () => resolve(''),
				})
				return
			}
		} catch (e) {
			// ignore
		}

		try {
			if (typeof uni.chooseFile === 'function') {
				uni.chooseFile({
					count: 1,
					success: (r) => {
						const p = r?.tempFiles?.[0]?.path || r?.tempFiles?.[0]?.tempFilePath || ''
						resolve(p)
					},
					fail: () => resolve(''),
				})
				return
			}
		} catch (e) {
			// ignore
		}

		// #ifdef APP-PLUS
		try {
			if (typeof plus !== 'undefined' && plus?.io && typeof plus.io.chooseFile === 'function') {
				plus.io.chooseFile(
					{
						multiple: false,
						type: 'file',
					},
					(picked) => {
						const uri =
							typeof picked === 'string'
								? picked
								: (picked?.files && Array.isArray(picked.files) ? picked.files[0] : '')
						resolve(uri || '')
					},
					() => resolve('')
				)
				return
			}
		} catch (e) {
			// ignore
		}
		// #endif

		resolve('')
	})
}

function formatDate(d) {
	try {
		return d ? new Date(d).toLocaleString() : ''
	} catch (e) {
		return ''
	}
}

const primaryBtnStyle = {
	background: 'linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%)',
	border: 'none',
	width: '220px',
	height: '44px',
	boxShadow: '0 16px 30px rgba(78,205,196,.28)',
	fontWeight: '800',
}
const ghostBtnStyle = {
	background: 'rgba(255,255,255,.86)',
	border: '1px solid rgba(27,31,42,.10)',
	height: '38px',
	paddingLeft: '14px',
	paddingRight: '14px',
	fontWeight: '800',
	color: '#1b1f2a',
}
const ghostPrimaryBtnStyle = {
	...ghostBtnStyle,
	background: 'rgba(78,205,196,.12)',
	border: '1px solid rgba(78,205,196,.35)',
	color: '#0e6f69',
}

const editBtnStyle = {
	background: '#ffffff',
	border: '1px solid rgba(27,31,42,.12)',
	padding: '0 10px',
	minWidth: '64px',
	height: '28px',
	fontSize: '12px',
	fontWeight: '700',
	color: '#1b1f2a',
}

const inputStyle = {
	background: 'rgba(255,255,255,.86)',
	border: '1px solid rgba(27,31,42,.10)',
	borderRadius: '14px',
	padding: '10px 12px',
	fontWeight: '700',
}

const textareaStyle = {
	...inputStyle,
	minHeight: '72px',
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	padding: 14px 14px 24px;
	background:
		radial-gradient(900rpx 520rpx at 15% 8%, rgba(102, 217, 232, 0.26), transparent 60%),
		radial-gradient(860rpx 520rpx at 85% 16%, rgba(78, 205, 196, 0.22), transparent 58%),
		linear-gradient(180deg, rgba(255, 255, 255, 1) 0%, rgba(245, 251, 251, 1) 55%, rgba(255, 255, 255, 1) 100%);
}

.card {
	background: rgba(255, 255, 255, 0.92);
	border: 1px solid rgba(27, 31, 42, 0.08);
	border-radius: 18px;
	padding: 14px;
	box-shadow: 0 22px 42px rgba(20, 27, 61, 0.10);
	margin-bottom: 12px;
}

.card-hd {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
	margin-bottom: 6px;
}

.result-title-row {
	display: flex;
	align-items: center;
	gap: 8px;
}

.quality-badge {
	font-size: 11px;
	font-weight: 900;
	padding: 3px 8px;
	border-radius: 999px;
	background: rgba(255, 193, 7, 0.18);
	color: rgba(121, 79, 0, 0.95);
	border: 1px solid rgba(255, 193, 7, 0.45);
}

.warn {
	margin-top: 8px;
	font-size: 12px;
	font-weight: 800;
	line-height: 1.5;
	color: rgba(121, 79, 0, 0.95);
	background: rgba(255, 193, 7, 0.14);
	border: 1px solid rgba(255, 193, 7, 0.35);
	border-radius: 12px;
	padding: 8px 10px;
}

.card-title {
	font-size: 16px;
	font-weight: 900;
	color: #1b1f2a;
}

.card-title {
	font-size: 18px;
	font-weight: 900;
	color: #1b1f2a;
}

.card-sub {
	margin-top: 6px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
	line-height: 1.5;
}

.section-title {
	font-size: 15px;
	font-weight: 900;
	color: #1b1f2a;
	margin-bottom: 10px;
}

.field {
	padding: 10px 0;
}

.label {
	font-size: 13px;
	font-weight: 900;
	color: rgba(27, 31, 42, 0.62);
	margin-bottom: 8px;
}

.value-text {
	font-size: 14px;
	font-weight: 800;
	color: #1b1f2a;
	padding: 6px 2px 2px;
}

.value-text-multi {
	line-height: 1.6;
	white-space: pre-wrap;
}

.upload-row {
	margin-top: 10px;
}

.section-sub {
	margin-top: 16px;
	font-size: 14px;
	font-weight: 900;
	color: #1b1f2a;
}

.mode-row {
	display: flex;
	gap: 10px;
	margin-bottom: 10px;
}

.mode {
	flex: 1;
	text-align: center;
	padding: 10px 0;
	border-radius: 999px;
	border: 1px solid rgba(27, 31, 42, 0.10);
	font-weight: 900;
	color: rgba(27, 31, 42, 0.72);
	background: rgba(255, 255, 255, 0.70);
}

.mode.active {
	border-color: rgba(78, 205, 196, 0.45);
	background: rgba(78, 205, 196, 0.12);
	color: #0e6f69;
}

.block {
	margin-top: 6px;
}

.hint {
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
	margin-bottom: 10px;
}

.muted {
	font-size: 12px;
	color: rgba(27, 31, 42, 0.45);
	padding: 6px 0;
}

.list {
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.item {
	padding: 12px;
	border-radius: 14px;
	border: 1px solid rgba(27, 31, 42, 0.08);
	background: rgba(255, 255, 255, 0.78);
}

.item.selected {
	border-color: rgba(78, 205, 196, 0.55);
	background: rgba(78, 205, 196, 0.10);
}

.item-hd {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
}

.item-title {
	font-size: 15px;
	font-weight: 900;
	color: #1b1f2a;
	flex: 1;
	min-width: 0;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.badge {
	font-size: 12px;
	font-weight: 900;
	padding: 4px 10px;
	border-radius: 999px;
	background: rgba(78, 205, 196, 0.22);
	color: #0e6f69;
	flex: 0 0 auto;
}

.item-sub {
	margin-top: 8px;
	font-size: 13px;
	color: rgba(27, 31, 42, 0.62);
	line-height: 1.35;
	word-break: break-all;
}

.item-time {
	margin-top: 8px;
	font-size: 11px;
	color: rgba(27, 31, 42, 0.42);
}


.actions {
	padding-top: 14px;
	display: flex;
	justify-content: center;
}

.generating {
	margin-top: 10px;
	text-align: center;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.story-title {
	margin-top: 8px;
	font-size: 16px;
	font-weight: 900;
	color: #1b1f2a;
}

.copy-row {
	display: flex;
	gap: 10px;
	margin-top: 12px;
	flex-wrap: wrap;
}

.chapter {
	margin-top: 14px;
	padding-top: 14px;
	border-top: 1px solid rgba(27, 31, 42, 0.06);
}

.chapter-title {
	font-size: 15px;
	font-weight: 900;
	color: #1b1f2a;
	margin-bottom: 8px;
}

.para {
	font-size: 13px;
	color: rgba(27, 31, 42, 0.72);
	line-height: 1.65;
	padding: 6px 0;
	word-break: break-word;
}

.milestone {
	margin-top: 10px;
	padding: 12px;
	border-radius: 14px;
	border: 1px solid rgba(27, 31, 42, 0.08);
	background: rgba(255, 255, 255, 0.75);
}

.milestone-title {
	font-size: 14px;
	font-weight: 900;
	color: #1b1f2a;
}

.milestone-sub {
	margin-top: 6px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.62);
	line-height: 1.5;
}

</style>
