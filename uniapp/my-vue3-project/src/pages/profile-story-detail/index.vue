<template>
	<view class="page">
		<view class="card">
			<view class="card-title">档案详情</view>
			<view class="card-sub">支持复制全文、导出、分享、删除</view>
		</view>

		<view class="card" v-if="loading">
			<view class="muted">正在加载…</view>
		</view>

		<view class="card" v-else-if="!story">
			<view class="muted">未找到档案内容</view>
		</view>

		<view class="card" v-else>
			<view class="detail-hd">
				<view class="story-title" v-if="story.title">{{ story.title }}</view>
				<u-button type="default" shape="circle" :customStyle="editBtnStyle" :loading="saving" @click="toggleEdit">{{ isEditing ? '保存' : '编辑' }}</u-button>
			</view>

			<view class="field" style="padding-top: 6px;">
				<view class="label">姓名</view>
				<view v-if="!isEditing" class="value-text">{{ displayText(profileForm.name) }}</view>
				<u-input v-else v-model="profileForm.name" placeholder="例如：小明" border="none" :customStyle="inputStyle" />
			</view>
			<view class="field">
				<view class="label">学习目标</view>
				<view v-if="!isEditing" class="value-text">{{ displayText(profileForm.learningGoal) }}</view>
				<u-input v-else v-model="profileForm.learningGoal" placeholder="例如：每天进步一点点" border="none" :customStyle="inputStyle" />
			</view>
			<view class="field">
				<view class="label">学习偏好</view>
				<view v-if="!isEditing" class="value-text value-text-multi">{{ displayText(profileForm.preferences) }}</view>
				<u-input v-else v-model="profileForm.preferences" type="textarea" autoHeight :maxlength="200" :showConfirmBar="false" placeholder="例如：科学、语文、英语" border="none" :customStyle="textareaStyle" />
			</view>

			<view class="meta-row">
				<view class="meta-item">storyId：{{ storyId }}</view>
				<view class="meta-item">保存时间：{{ formatDate(savedAt) }}</view>
			</view>

			<view class="copy-row">
				<u-button type="default" shape="circle" :customStyle="ghostBtnStyle" @click="copyAll">复制全文</u-button>
				<u-button type="default" shape="circle" :customStyle="ghostBtnStyle" :loading="exporting" @click="doExport">导出</u-button>
			</view>
			<view class="copy-row" style="margin-top:10px;">
				<u-button type="primary" shape="circle" :customStyle="ghostPrimaryBtnStyle" :loading="sharing" @click="doShare">分享</u-button>
				<u-button v-if="share.status === 'active'" type="default" shape="circle" :customStyle="dangerBtnStyle" :loading="revoking" @click="confirmRevoke">取消分享</u-button>
				<u-button v-else type="default" shape="circle" :customStyle="dangerBtnStyle" :loading="deleting" @click="confirmDelete">删除</u-button>
			</view>
			<view v-if="share.status" class="share-tip">
				分享状态：{{ share.status }}<text v-if="share.expiresAt">（到期：{{ formatDate(share.expiresAt) }}）</text>
			</view>

			<view v-if="Array.isArray(story.chapters) && story.chapters.length" class="chapters">
				<view v-for="(ch, idx) in story.chapters" :key="idx" class="chapter">
					<view class="chapter-title">{{ ch.chapterTitle || `第${idx + 1}章` }}</view>
					<view v-if="Array.isArray(ch.paragraphs)" class="paras">
						<view v-for="(p, pi) in ch.paragraphs" :key="pi" class="para">{{ p }}</view>
					</view>
				</view>
			</view>

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
import { onLoad } from '@dcloudio/uni-app'
import { reactive, ref } from 'vue'
import {
	apiCreateProfileStoryShare,
	apiDeleteProfileStory,
	apiExportProfileStoryWord,
	apiGetProfileStory,
	apiRevokeProfileShare,
	apiUpdateProfileStory,
} from '@/services/api'
import { buildShareFullUrl } from '@/services/profileShare'

const storyId = ref('')
const story = ref(null)
const savedAt = ref('')
const loading = ref(false)
const deleting = ref(false)

const saving = ref(false)
const isEditing = ref(false)
const profileForm = reactive({ name: '', learningGoal: '', preferences: '' })

const exporting = ref(false)
const sharing = ref(false)
const revoking = ref(false)

const lastExport = ref({ exportId: '', fileUrl: '', pdfUrl: '', fileName: '', pdfFileName: '' })
const share = ref({ status: '', shareId: '', shareUrl: '', expiresAt: '' })

onLoad((query) => {
	storyId.value = query?.storyId ? String(query.storyId) : ''
	fetchDetail()
})

async function fetchDetail() {
	if (!storyId.value) return
	loading.value = true
	try {
		const res = await apiGetProfileStory(storyId.value)
		const data = res?.data || null
		story.value = data?.story || data || null
		savedAt.value = data?.savedAt || data?.createdAt || ''
		const p = story.value?.profile || {}
		profileForm.name = String(p?.name || '')
		profileForm.learningGoal = String(p?.learningGoal || '')
		profileForm.preferences = String(p?.preferences || '')
		// 可选：如果后端将分享信息一起返回，则自动填充（兼容）
		if (data?.share) {
			share.value = { ...share.value, ...(data.share || {}) }
		}
	} catch (e) {
		console.error('get story detail error', e)
		story.value = null
		const status = Number(e?.status || e?.statusCode)
		if (status === 401) {
			uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
		} else if (status === 404) {
			uni.showToast({ title: '当前账号下未找到该档案', icon: 'none' })
		} else {
			uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
		}
	} finally {
		loading.value = false
	}
}

async function saveEdits() {
	if (!storyId.value || !story.value) return
	saving.value = true
	try {
		const nextProfile = {
			name: String(profileForm.name || '').trim(),
			learningGoal: String(profileForm.learningGoal || '').trim(),
			preferences: String(profileForm.preferences || '').trim(),
		}
		story.value.profile = nextProfile
		await apiUpdateProfileStory(storyId.value, { profile: nextProfile, story: story.value })
		uni.showToast({ title: '已保存修改', icon: 'none' })
		return true
	} catch (e) {
		console.error('update story error', e)
		uni.showToast({ title: e?.message || '保存失败（请确认后端已实现 update 接口）', icon: 'none' })
		return false
	} finally {
		saving.value = false
	}
}

function displayText(v) {
	const s = String(v || '').trim()
	return s ? s : '未填写'
}

async function toggleEdit() {
	if (isEditing.value) {
		const ok = await saveEdits()
		if (ok) isEditing.value = false
		return
	}
	isEditing.value = true
}

async function doExport() {
	if (!storyId.value) return
	exporting.value = true
	try {
		const res = await apiExportProfileStoryWord(storyId.value)
		const d = res?.data || {}
		lastExport.value = {
			exportId: d.exportId || '',
			fileUrl: d.fileUrl || '',
			pdfUrl: d.pdfUrl || '',
			fileName: d.fileName || '',
			pdfFileName: d.pdfFileName || '',
		}
		const actions = []
		if (lastExport.value.pdfUrl) actions.push('预览PDF')
		if (lastExport.value.fileUrl) actions.push('下载Word')
		if (!actions.length) {
			uni.showToast({ title: '导出成功，但未返回下载链接', icon: 'none' })
			return
		}
		uni.showActionSheet({
			itemList: actions,
			success: (r) => {
				const pick = actions[r.tapIndex]
				if (pick === '预览PDF') {
					try {
						if (typeof window !== 'undefined' && window.open) window.open(lastExport.value.pdfUrl)
						else uni.setClipboardData({ data: lastExport.value.pdfUrl })
					} catch (e) {
						uni.setClipboardData({ data: lastExport.value.pdfUrl })
					}
				}
				if (pick === '下载Word') {
					// 直接交给系统打开下载链接（H5 会新开；小程序按平台能力处理）
					try {
						if (typeof window !== 'undefined' && window.open) window.open(lastExport.value.fileUrl)
						else uni.setClipboardData({ data: lastExport.value.fileUrl })
					} catch (e) {
						uni.setClipboardData({ data: lastExport.value.fileUrl })
					}
				}
			},
			fail: () => {},
		})
	} catch (e) {
		console.error('export story error', e)
		uni.showToast({ title: '导出失败', icon: 'none' })
	} finally {
		exporting.value = false
	}
}

async function doShare() {
	if (!storyId.value) return
	sharing.value = true
	try {
		const payload = {
			expiresInDays: 7,
			...(lastExport.value.exportId ? { exportId: lastExport.value.exportId } : {}),
		}
		const res = await apiCreateProfileStoryShare(storyId.value, payload)
		const d = res?.data || {}
		share.value = {
			status: d.status || 'active',
			shareId: d.shareId || '',
			shareUrl: d.shareUrl || '',
			expiresAt: d.expiresAt || '',
		}

		// 优先使用后端返回的完整链接（可避免前端 localhost 拼接问题）
		const shareFullUrl = d.shareFullUrl ? String(d.shareFullUrl) : buildShareFullUrl(share.value.shareUrl)

		uni.showModal({
			title: '分享链接已生成',
			content: shareFullUrl,
			confirmText: '复制链接',
			cancelText: '打开',
			success: (r) => {
				if (r.confirm) {
					uni.setClipboardData({ data: shareFullUrl })
					return
				}
				// cancel -> 打开分享页（/view 页面由后端提供预览与下载按钮）
				try {
					if (typeof window !== 'undefined' && window.open) window.open(shareFullUrl)
					else uni.setClipboardData({ data: shareFullUrl })
				} catch (e) {
					uni.setClipboardData({ data: shareFullUrl })
				}
			},
		})
	} catch (e) {
		console.error('create share error', e)
		uni.showToast({ title: '分享失败', icon: 'none' })
	} finally {
		sharing.value = false
	}
}

function confirmRevoke() {
	if (!share.value.shareId) return
	uni.showModal({
		title: '取消分享',
		content: '确定撤销该分享链接吗？撤销后外部访问将返回 410。',
		success: async (r) => {
			if (!r.confirm) return
			await doRevoke()
		},
	})
}

async function doRevoke() {
	if (!share.value.shareId) return
	revoking.value = true
	try {
		const res = await apiRevokeProfileShare(share.value.shareId)
		share.value.status = res?.data?.status || 'revoked'
		uni.showToast({ title: '已撤销分享', icon: 'none' })
	} catch (e) {
		console.error('revoke share error', e)
		uni.showToast({ title: '撤销失败', icon: 'none' })
	} finally {
		revoking.value = false
	}
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

function confirmDelete() {
	uni.showModal({
		title: '删除档案',
		content: '确定要删除这条成长档案吗？删除后不可恢复。',
		success: async (r) => {
			if (!r.confirm) return
			await doDelete()
		},
	})
}

async function doDelete() {
	if (!storyId.value) return
	deleting.value = true
	try {
		await apiDeleteProfileStory(storyId.value)
		uni.showToast({ title: '已删除', icon: 'none' })
		setTimeout(() => {
			uni.navigateBack()
		}, 300)
	} catch (e) {
		console.error('delete story error', e)
		uni.showToast({ title: '删除失败', icon: 'none' })
	} finally {
		deleting.value = false
	}
}

function formatDate(d) {
	try {
		return d ? new Date(d).toLocaleString() : ''
	} catch (e) {
		return ''
	}
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

const dangerBtnStyle = {
	...ghostBtnStyle,
	background: 'rgba(255,77,79,.10)',
	border: '1px solid rgba(255,77,79,.30)',
	color: '#a8071a',
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	padding: 18px 16px;
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
	box-shadow: 0 22px 42px rgba(20, 27, 61, 0.12);
	margin-bottom: 12px;
}

.card-title {
	font-size: 18px;
	font-weight: 900;
	color: #1b1f2a;
	text-align: center;
}

.card-sub {
	margin-top: 8px;
	font-size: 13px;
	color: rgba(27, 31, 42, 0.5);
	text-align: center;
}

.story-title {
	font-size: 18px;
	font-weight: 900;
	color: #1b1f2a;
	text-align: center;
	margin-bottom: 10px;
}

.detail-hd {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
}

.meta-row {
	margin: 8px 0 12px;
	padding: 10px 12px;
	border-radius: 14px;
	border: 1px solid rgba(27,31,42,.08);
	background: rgba(255,255,255,.86);
}

.meta-item {
	font-size: 12px;
	color: rgba(27,31,42,.60);
	margin: 4px 0;
}

.copy-row {
	display: flex;
	gap: 10px;
	justify-content: center;
	align-items: center;
	margin-bottom: 12px;
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

.chapter {
	padding: 12px 12px;
	border-radius: 14px;
	border: 1px solid rgba(27,31,42,.08);
	background: rgba(255,255,255,.86);
	margin-bottom: 10px;
}

.chapter-title {
	font-size: 15px;
	font-weight: 900;
	color: #1b1f2a;
}

.para {
	margin-top: 8px;
	font-size: 14px;
	line-height: 1.65;
	color: rgba(27,31,42,.86);
}

.section-sub {
	margin: 12px 0 8px;
	font-size: 14px;
	font-weight: 900;
	color: #1b1f2a;
}

.milestone {
	padding: 10px 12px;
	border-radius: 14px;
	border: 1px solid rgba(27,31,42,.08);
	background: rgba(255,255,255,.86);
	margin-bottom: 10px;
}

.milestone-title {
	font-size: 14px;
	font-weight: 900;
	color: #1b1f2a;
}

.milestone-sub {
	margin-top: 6px;
	font-size: 12px;
	color: rgba(27,31,42,.60);
}

.muted {
	font-size: 13px;
	color: rgba(27, 31, 42, 0.55);
	text-align: center;
	padding: 14px 0;
}
</style>
