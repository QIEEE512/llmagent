<template>
	<view class="page">
		<view class="hd">
			<view class="title">数字卡通形象</view>
			<view class="sub" v-if="loggedIn">按步骤采集外貌、画像与声线，生成儿童审美的卡通数字人</view>
			<view class="sub" v-else>该功能需要登录才能使用</view>
		</view>

		<!-- 未登录拦截态 -->
		<view v-if="!loggedIn" class="card">
			<view class="card-title">需要登录</view>
			<view class="card-sub">登录后才能创建你的专属卡通形象与声线</view>
			<view class="actions">
				<u-button type="primary" shape="circle" :customStyle="btnStyle" @tap="goLogin">去登录</u-button>
				<u-button type="default" shape="circle" :customStyle="ghostBtnStyle" @tap="goBack">返回</u-button>
			</view>
		</view>

		<!-- 登录后：分步向导 -->
		<view v-else class="card">
			<view class="stepbar">
				<view class="step">Step {{ step }} / 4</view>
				<view class="step-title">{{ stepTitle }}</view>
			</view>

			<!-- Step 1：外貌照片 -->
			<view v-if="step === 1" class="section">
				<view class="hint">建议正脸、光线充足、无遮挡。支持拍照或相册选取。</view>
				<view class="btn-row">
					<u-button type="primary" shape="circle" :customStyle="smallBtnStyle" :loading="loading.photo" @tap="pickFromCamera">拍照</u-button>
					<u-button type="default" shape="circle" :customStyle="smallGhostBtnStyle" :loading="loading.photo" @tap="pickFromAlbum">从相册选择</u-button>
				</view>

				<view v-if="portrait.localPath" class="preview">
					<image class="preview-img" :src="portrait.localPath" mode="aspectFill" />
					<view class="preview-meta" v-if="portrait.fileUrl">已上传：{{ portrait.fileUrl }}</view>
					<view class="preview-meta" v-else>已选择图片，尚未上传</view>
				</view>
			</view>

			<!-- Step 2：画像问答 -->
			<view v-else-if="step === 2" class="section">
				<view class="field">
					<view class="label">年龄（3-12）</view>
					<u-input v-model="profile.age" type="number" placeholder="例如：8" border="none" :customStyle="inputStyle" />
				</view>
				<view class="field">
					<view class="label">兴趣（可多选）</view>
					<view class="chips">
						<view v-for="tag in interestPool" :key="tag" class="chip" :class="{ on: profile.interests.includes(tag) }" @tap="toggleInterest(tag)">{{ tag }}</view>
					</view>
					<u-input v-model="profile.customInterest" placeholder="自定义兴趣（可选）" border="none" :customStyle="inputStyle" />
				</view>
				<view class="field">
					<view class="label">性格/风格</view>
					<view class="chips">
						<view v-for="s in stylePool" :key="s" class="chip" :class="{ on: profile.style === s }" @tap="profile.style = s">{{ s }}</view>
					</view>
				</view>
				<view class="field">
					<view class="label">补充描述（可选）</view>
					<u-input v-model="profile.freeText" type="textarea" autoHeight :maxlength="200" :showConfirmBar="false" placeholder="例如：喜欢蓝色，希望有小披风" border="none" :customStyle="textareaStyle" />
				</view>
			</view>

			<!-- Step 3：声线（预设/录音） -->
			<view v-else-if="step === 3" class="section">
				<view class="seg">
					<view class="seg-item" :class="{ on: voice.mode === 'preset' }" @tap="voice.mode = 'preset'">预设声线</view>
					<view class="seg-item" :class="{ on: voice.mode === 'record' }" @tap="voice.mode = 'record'">录音采集</view>
				</view>

				<view v-if="voice.mode === 'preset'">
					<view class="hint">选择一个你喜欢的声音风格。</view>
					<view class="voice-list">
						<view v-for="v in voicePresets" :key="v.id" class="voice-item" :class="{ on: voice.presetId === v.id }" @tap="selectPreset(v.id)">
							<view class="voice-name">{{ v.name }}</view>
							<view class="voice-sub">{{ v.desc }}</view>
						</view>
					</view>
				</view>

				<view v-else>
					<view class="hint">录音后会上传并提取声线特征（voiceProfileId），同时推荐最匹配的预设。</view>
					<view class="record-card" :class="{ recording: record.recording }">
						<view class="record-title">{{ record.recording ? '正在录音…' : record.localPath ? '录音完成' : '尚未录音' }}</view>
						<view class="record-sub">建议朗读 5-10 秒："你好，我是你的学习小伙伴。"</view>
						<view class="btn-row">
							<u-button type="primary" shape="circle" :customStyle="smallBtnStyle" :loading="loading.voice" @tap="toggleRecord">{{ record.recording ? '结束录音' : '开始录音' }}</u-button>
							<u-button v-if="record.localPath" type="default" shape="circle" :customStyle="smallGhostBtnStyle" @tap="resetRecord" :disabled="loading.voice">重录</u-button>
							<u-button v-else type="default" shape="circle" :customStyle="smallGhostBtnStyle" :disabled="true">重录</u-button>
						</view>
						<view v-if="record.voiceUrl" class="record-meta">已上传：{{ record.voiceUrl }}</view>
						<view v-if="voice.voiceProfileId" class="record-meta">voiceProfileId：{{ voice.voiceProfileId }}</view>
					</view>
				</view>

				<u-input v-model="voice.note" placeholder="可选：声音偏好补充（例如更慢、更温柔）" border="none" :customStyle="inputStyle" />
			</view>

			<!-- Step 4：生成与预览 + 视频 -->
			<view v-else class="section">
				<view class="summary">
					<view class="sum-row"><text class="k">外貌</text><text class="v">{{ portrait.fileUrl ? '已上传' : '未完成' }}</text></view>
					<view class="sum-row"><text class="k">年龄</text><text class="v">{{ profile.age || '-' }}</text></view>
					<view class="sum-row"><text class="k">兴趣</text><text class="v">{{ summaryInterests }}</text></view>
					<view class="sum-row"><text class="k">声线</text><text class="v">{{ currentVoiceName }}</text></view>
				</view>

				<!-- 生成中动画：头像生成 / 视频生成 -->
				<view v-if="loading.generate || (video.jobId && !video.videoUrl)" class="loading-card">
					<view class="loading-left">
						<view class="spinner" />
					</view>
					<view class="loading-right">
						<view class="loading-title">正在生成中…</view>
						<view class="loading-sub" v-if="loading.generate">卡通形象生成可能需要几十秒，请不要退出页面</view>
						<view class="loading-sub" v-else>动态头像/视频正在排队与渲染中，会自动刷新结果</view>
					</view>
				</view>

				<view v-if="result.imageUrl" class="preview">
					<image class="preview-img" :src="displayImageUrl" mode="aspectFill" />
					<view class="btn-row" style="grid-template-columns: 1fr; margin-top: 10px;">
						<u-button type="primary" shape="circle" :customStyle="btnStyle" @tap="saveAndReturnToChat">保存并返回聊天</u-button>
					</view>
				</view>
				<view v-else class="hint">点击下方按钮开始生成（同步生成，可能需要几十秒）</view>

				<view class="video-card">
					<view class="video-title">动态头像 / 视频</view>
					<view class="hint">基于当前头像图生成一段短视频。生成完成后会自动切换为视频预览，并保留静态图。</view>
					<u-input v-model="video.prompt" placeholder="可选：描述想要的动态效果（例如：眨眼、挥手）" border="none" :customStyle="inputStyle" />
					<view class="btn-row" style="margin-top: 10px; grid-template-columns: 1fr;">
						<u-button type="primary" shape="circle" :customStyle="btnStyle" :loading="loading.video" :disabled="!canGenerateVideo" @tap="onGenerateVideo">{{ video.videoUrl ? '重新生成视频' : '生成动态头像/视频' }}</u-button>
					</view>
					<view v-if="video.jobId && !video.videoUrl" class="video-loading-row">
						<view class="spinner spinner-sm" />
						<text class="video-loading-text">视频生成中…（{{ video.status || 'pending' }}）</text>
					</view>
					<view v-if="video.videoUrl" class="video-preview">
						<video class="video" :src="displayVideoUrl" controls :poster="displayImageUrl || ''" @error="video.videoError = true" />
					</view>
					<view v-else-if="result.imageUrl" class="video-preview" style="background: transparent; border: none;">
						<image class="preview-img" :src="displayImageUrl" mode="aspectFill" />
						<view class="preview-meta">视频未就绪，显示静态图</view>
					</view>
				</view>

				<view class="draft-actions">
					<view class="draft-tip">草稿会自动保存到本机</view>
					<text class="draft-clear" @tap="clearDraft">清空草稿</text>
				</view>
			</view>

			<!-- 底部操作区 -->
			<view class="actions">
				<u-button type="default" shape="circle" :customStyle="ghostBtnStyle" @tap="prevStep" :disabled="step === 1 || loading.any">上一步</u-button>
				<u-button v-if="step < 4" type="primary" shape="circle" :customStyle="btnStyle" :disabled="!canNext || loading.any" :loading="loading.any" @tap="nextStep">下一步</u-button>
				<u-button v-else type="primary" shape="circle" :customStyle="btnStyle" :loading="loading.generate" :disabled="!canGenerate || loading.generate" @tap="onGenerate">{{ result.imageUrl ? '重新生成' : '生成卡通形象' }}</u-button>
			</view>
		</view>

		<u-toast ref="toastRef" />
	</view>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { onHide, onShow, onUnload } from '@dcloudio/uni-app'

import { apiAvatarGenerate, apiAvatarVideoGenerateByImage, apiAvatarVideoStatus, apiUploadAvatarImage, apiUploadVoice, apiVoiceAnalyze } from '@/services/api'
import { getToken } from '@/services/storage'

const toastRef = ref(null)
const loggedIn = ref(!!getToken())

const DRAFT_KEY = 'avatar_custom_draft_v1'
const ACTIVE_AVATAR_KEY = 'active_avatar'
const VIDEO_JOB_KEY = 'avatar_video_job_v1'

// 图片/视频文件经常以 "/files/..." 形式返回；在 <image>/<video> 里需要绝对地址，否则会显示空白。
const FILE_ORIGIN = 'https://jkyhobdhqqah.sealoshzh.site'

// 后端接口通常约束：传入的 fileUrl/imageUrl 必须是本服务返回的 "/files/..." 形式。
// 注意：toAbsFileUrl 仅用于 <image>/<video> 展示；请求 API 时不要把 /files 转为绝对地址。
function toApiFileUrl(u) {
	if (!u) return ''
	const s = String(u)
	// 已经是后端需要的相对路径
	if (s.startsWith('/files/')) return s
	// 兼容返回了完整 URL 的情况：提取出 /files/... 部分
	const i = s.indexOf('/files/')
	if (i >= 0) return s.slice(i)
	return s
}

function toAbsFileUrl(u) {
	if (!u) return ''
	const s = String(u)
	if (/^https?:\/\//i.test(s) || /^data:/i.test(s) || /^blob:/i.test(s)) return s
	if (s.startsWith('//')) return `https:${s}`
	if (s.startsWith('/')) return FILE_ORIGIN + s
	return FILE_ORIGIN + '/' + s
}

const step = ref(1)

const portrait = reactive({ localPath: '', fileUrl: '' })
const profile = reactive({ age: '', interests: [], customInterest: '', style: '活泼', freeText: '' })

const voice = reactive({
	mode: 'preset',
	presetId: 'kid_bright_01',
	voiceProfileId: '',
	note: '',
})

const record = reactive({ recording: false, localPath: '', voiceUrl: '', durationMs: 0 })
const result = reactive({ avatarId: '', imageUrl: '' })

const video = reactive({
	jobId: '',
	status: '',
	videoUrl: '',
	prompt: '',
	videoError: false,
})

const loading = reactive({
	photo: false,
	generate: false,
	voice: false,
	video: false,
	get any() {
		return !!(this.photo || this.generate || this.voice || this.video)
	},
})

const interestPool = ['恐龙', '宇宙', '公主', '画画', '数学', '英语', '足球', '钢琴', '科学', '故事']
const stylePool = ['活泼', '温柔', '酷酷', '搞怪', '学霸']
const voicePresets = [
	{ id: 'kid_bright_01', name: '活泼童声-小太阳', desc: '清亮、元气、偏快' },
	{ id: 'kid_gentle_01', name: '温柔童声-小云朵', desc: '柔和、亲切、偏慢' },
	{ id: 'narration_warm_01', name: '暖心旁白-故事时间', desc: '讲故事风格、节奏稳定' },
]

// 兼容保留：旧版模板式视频生成已下线为“基于 imageUrl 的最小契约”

const stepTitle = computed(() => (step.value === 1 ? '外貌采集' : step.value === 2 ? '画像问答' : step.value === 3 ? '声线设置' : '生成与预览'))

const summaryInterests = computed(() => {
	const list = [...profile.interests]
	if (profile.customInterest?.trim()) list.push(profile.customInterest.trim())
	return list.length ? list.join('、') : '-'
})

const currentVoiceName = computed(() => {
	const v = voicePresets.find((x) => x.id === voice.presetId)
	return v?.name || '未选择'
})

const canNext = computed(() => {
	if (step.value === 1) return !!portrait.fileUrl
	if (step.value === 2) {
		const age = Number(profile.age)
		return age >= 3 && age <= 12
	}
	if (step.value === 3) return voice.mode === 'record' ? !!(voice.voiceProfileId || voice.presetId) : !!voice.presetId
	return true
})

const canGenerate = computed(() => {
	const age = Number(profile.age)
	return !!portrait.fileUrl && age >= 3 && age <= 12 && !!(voice.voiceProfileId || voice.presetId)
})

const canGenerateVideo = computed(() => {
	return !!result.avatarId && !!result.imageUrl && !loading.video
})

const displayImageUrl = computed(() => toAbsFileUrl(result.imageUrl))
const displayVideoUrl = computed(() => toAbsFileUrl(video.videoUrl))

const inputStyle = {
	background: 'rgba(255,255,255,.78)',
	borderRadius: '12px',
	padding: '10px 12px',
	border: '1px solid rgba(27,31,42,.08)',
}

const textareaStyle = { ...inputStyle, minHeight: '88px' }

const btnStyle = {
	background: 'linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%)',
	border: 'none',
	width: '100%',
	height: '44px',
	marginTop: '0px',
	boxShadow: '0 16px 30px rgba(78, 205, 196, .28)',
	fontWeight: '800',
}

const ghostBtnStyle = {
	width: '100%',
	height: '44px',
	borderRadius: '999px',
	background: 'rgba(255,255,255,.85)',
	border: '1px solid rgba(27,31,42,.10)',
	fontWeight: '800',
}

const smallBtnStyle = {
	background: 'linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%)',
	border: 'none',
	width: '100%',
	height: '40px',
	boxShadow: '0 14px 26px rgba(78, 205, 196, .22)',
	fontWeight: '800',
}

const smallGhostBtnStyle = {
	width: '100%',
	height: '40px',
	borderRadius: '999px',
	background: 'rgba(255,255,255,.85)',
	border: '1px solid rgba(27,31,42,.10)',
	fontWeight: '800',
}

function tip(msg, opts) {
	try {
		if (toastRef.value && typeof toastRef.value.show === 'function') {
			toastRef.value.show({ message: msg, ...(opts || {}) })
			return
		}
	} catch (e) {}
	uni.showToast({ title: String(msg || ''), icon: 'none', duration: 2200 })
}

function refreshLogin() {
	loggedIn.value = !!getToken()
}

function goLogin() {
	uni.navigateTo({ url: '/pages/login/index' })
}

function goBack() {
	uni.navigateBack()
}

function safeGetStorage(key) {
	try {
		return uni.getStorageSync(key)
	} catch (e) {
		return null
	}
}

function safeSetStorage(key, val) {
	try {
		uni.setStorageSync(key, val)
	} catch (e) {}
}

function safeRemoveStorage(key) {
	try {
		uni.removeStorageSync(key)
	} catch (e) {}
}

function buildDraft() {
	return {
		step: step.value,
		portrait: { localPath: portrait.localPath, fileUrl: portrait.fileUrl },
		profile: {
			age: profile.age,
			interests: Array.isArray(profile.interests) ? profile.interests : [],
			customInterest: profile.customInterest,
			style: profile.style,
			freeText: profile.freeText,
		},
		voice: { mode: voice.mode, presetId: voice.presetId, voiceProfileId: voice.voiceProfileId, note: voice.note },
		record: { localPath: record.localPath, voiceUrl: record.voiceUrl, durationMs: record.durationMs },
		video: {
			jobId: video.jobId,
			status: video.status,
			videoUrl: video.videoUrl,
			prompt: video.prompt,
			videoError: video.videoError,
		},
		result: { avatarId: result.avatarId, imageUrl: result.imageUrl },
		updatedAt: Date.now(),
	}
}

function saveDraft() {
	if (!loggedIn.value) return
	safeSetStorage(DRAFT_KEY, buildDraft())
}

function loadDraft() {
	const d = safeGetStorage(DRAFT_KEY)
	if (!d || typeof d !== 'object') return false
	try {
		step.value = Number(d.step) >= 1 && Number(d.step) <= 4 ? Number(d.step) : 1
		portrait.localPath = String(d?.portrait?.localPath || '')
		portrait.fileUrl = String(d?.portrait?.fileUrl || '')
		profile.age = String(d?.profile?.age || '')
		profile.interests = Array.isArray(d?.profile?.interests) ? [...d.profile.interests] : []
		profile.customInterest = String(d?.profile?.customInterest || '')
		profile.style = String(d?.profile?.style || profile.style)
		profile.freeText = String(d?.profile?.freeText || '')
		voice.mode = String(d?.voice?.mode || voice.mode)
		voice.presetId = String(d?.voice?.presetId || voice.presetId)
		voice.voiceProfileId = String(d?.voice?.voiceProfileId || '')
		voice.note = String(d?.voice?.note || '')
		record.localPath = String(d?.record?.localPath || '')
		record.voiceUrl = String(d?.record?.voiceUrl || '')
		record.durationMs = Number(d?.record?.durationMs || 0)
		video.jobId = String(d?.video?.jobId || '')
		video.status = String(d?.video?.status || '')
		video.videoUrl = String(d?.video?.videoUrl || '')
		video.prompt = String(d?.video?.prompt || '')
		video.videoError = !!d?.video?.videoError
		result.avatarId = String(d?.result?.avatarId || '')
		result.imageUrl = String(d?.result?.imageUrl || '')
		return true
	} catch (e) {
		return false
	}
}

function clearDraft() {
	safeRemoveStorage(DRAFT_KEY)
	step.value = 1
	portrait.localPath = ''
	portrait.fileUrl = ''
	profile.age = ''
	profile.interests.splice(0, profile.interests.length)
	profile.customInterest = ''
	profile.style = '活泼'
	profile.freeText = ''
	voice.mode = 'preset'
	voice.presetId = 'kid_bright_01'
	voice.voiceProfileId = ''
	voice.note = ''
	record.recording = false
	record.localPath = ''
	record.voiceUrl = ''
	record.durationMs = 0
	video.jobId = ''
	video.status = ''
	video.videoUrl = ''
	video.prompt = ''
	video.videoError = false
	result.avatarId = ''
	result.imageUrl = ''
	tip('草稿已清空')
}

onMounted(() => {
	refreshLogin()
	if (!loggedIn.value) {
		tip('该功能需要登录才能使用')
		setTimeout(() => goLogin(), 250)
		return
	}
	if (loadDraft()) {
		try {
			uni.showToast({ title: '已恢复上次草稿', icon: 'none', duration: 1200 })
		} catch (e) {}
	}
})

onShow(() => {
	refreshLogin()
	if (loggedIn.value) {
		loadDraft()
		resumeVideoJobIfNeeded()
	}
})

let draftTimer = null
watch(
	[
		() => step.value,
		() => portrait.localPath,
		() => portrait.fileUrl,
		() => profile.age,
		() => profile.customInterest,
		() => profile.style,
		() => profile.freeText,
		() => voice.mode,
		() => voice.presetId,
		() => voice.voiceProfileId,
		() => voice.note,
		() => record.localPath,
		() => record.voiceUrl,
		() => String(record.durationMs),
		() => video.jobId,
		() => video.status,
		() => video.videoUrl,
		() => video.prompt,
		() => String(video.videoError),
		() => result.avatarId,
		() => result.imageUrl,
		() => profile.interests.join('|'),
	],
	() => {
		if (!loggedIn.value) return
		if (draftTimer) clearTimeout(draftTimer)
		draftTimer = setTimeout(() => saveDraft(), 350)
	}
)

function toggleInterest(tag) {
	const idx = profile.interests.indexOf(tag)
	if (idx >= 0) profile.interests.splice(idx, 1)
	else profile.interests.push(tag)
}

async function chooseImage(sourceType) {
	const choose = await new Promise((resolve, reject) => {
		uni.chooseImage({ count: 1, sourceType: [sourceType], success: resolve, fail: reject })
	})
	const tempFilePath = choose?.tempFilePaths?.[0]
	if (!tempFilePath) throw new Error('未选择图片')
	portrait.localPath = tempFilePath

	loading.photo = true
	try {
		const res = await apiUploadAvatarImage(tempFilePath)
		const url = res?.data?.url || res?.data?.fileUrl || res?.data?.file_url
		if (!url) throw new Error('上传失败：服务器未返回图片地址')
		portrait.fileUrl = url
		tip('图片已上传', { type: 'success' })
	} finally {
		loading.photo = false
	}
}

async function pickFromCamera() {
	try {
		await chooseImage('camera')
	} catch (err) {
		tip(err?.message || '拍照失败')
	}
}

async function pickFromAlbum() {
	try {
		await chooseImage('album')
	} catch (err) {
		tip(err?.message || '选择图片失败')
	}
}

function nextStep() {
	if (!canNext.value) {
		if (step.value === 1) return tip('请先选择并上传外貌照片')
		if (step.value === 2) return tip('请输入 3-12 的年龄')
		if (step.value === 3) return tip(voice.mode === 'record' ? '请完成录音并提取声线' : '请选择一个预设声线')
	}
	step.value = Math.min(4, step.value + 1)
}

function prevStep() {
	step.value = Math.max(1, step.value - 1)
}

function selectPreset(id) {
	voice.presetId = id
	if (voice.mode === 'preset') {
		voice.voiceProfileId = ''
	}
}

function resetRecord() {
	record.recording = false
	record.localPath = ''
	record.voiceUrl = ''
	record.durationMs = 0
	voice.voiceProfileId = ''
}

async function toggleRecord() {
	if (!uni.getRecorderManager) {
		return tip('当前平台暂不支持录音，请使用“预设声线”')
	}
	const recorder = uni.getRecorderManager()
	if (record.recording) {
		recorder.stop()
		return
	}
	loading.voice = true
	record.recording = true
	const startedAt = Date.now()

	try {
		await new Promise((resolve, reject) => {
			const onStop = async (res) => {
				try {
					record.recording = false
					record.localPath = res?.tempFilePath || ''
					record.durationMs = Date.now() - startedAt
					if (!record.localPath) throw new Error('录音失败：未返回文件路径')
					const up = await apiUploadVoice(record.localPath)
					const voiceUrl = up?.data?.url || up?.data?.fileUrl || up?.data?.file_url
					if (!voiceUrl) throw new Error('上传失败：未返回 voiceUrl')
					record.voiceUrl = voiceUrl
					const an = await apiVoiceAnalyze({ voiceUrl, mode: 'extract', preferPresets: true })
					voice.voiceProfileId = String(an?.data?.voiceProfileId || '')
					const rec = Array.isArray(an?.data?.recommendedPresets) ? an.data.recommendedPresets : []
					if (rec.length && rec[0]?.presetId) voice.presetId = String(rec[0].presetId)
					tip('声线已提取', { type: 'success' })
					resolve(null)
				} catch (e) {
					reject(e)
				}
			}
			const onError = (e) => reject(e)
			if (recorder.onceStop) recorder.onceStop(onStop)
			else recorder.onStop(onStop)
			if (recorder.onceError) recorder.onceError(onError)
			else recorder.onError(onError)
			recorder.start({ duration: 15000, format: 'wav' })
		})
	} catch (err) {
		record.recording = false
		tip(err?.message || '录音失败')
	} finally {
		loading.voice = false
	}
}

async function onGenerate() {
	if (!canGenerate.value) return tip('请先完成外貌、年龄与声线选择')
	loading.generate = true
	try {
		const ageNum = Number(profile.age)
		const interests = [...profile.interests]
		if (profile.customInterest?.trim()) interests.push(profile.customInterest.trim())

		const payload = {
			portraitUrl: portrait.fileUrl,
			profile: { age: ageNum, interests, style: profile.style, freeText: profile.freeText },
			voice: { voiceProfileId: voice.voiceProfileId || undefined, presetId: voice.presetId, note: voice.note },
			output: { characterStyle: 'kids_cartoon' },
		}
		const res = await apiAvatarGenerate(payload, 'user')
		const avatarId = res?.data?.avatarId || res?.data?.id || ''
		const imageUrl = res?.data?.imageUrl || res?.data?.url || ''
		if (!imageUrl) throw new Error('生成成功但未返回 imageUrl')
		result.avatarId = String(avatarId || '')
		result.imageUrl = String(imageUrl)
		saveDraft()
		tip('生成成功', { type: 'success' })
	} catch (err) {
		const msg = err?.message || err?.data?.detail || err?.data?.message || '生成失败'
		if (Number(err?.status) === 401) {
			tip('登录已过期，请重新登录')
			setTimeout(() => goLogin(), 200)
			return
		}
		tip(msg)
	} finally {
		loading.generate = false
	}
}

function saveAndReturnToChat() {
	if (!result.imageUrl) return tip('请先生成形象')
	const payload = { avatarId: result.avatarId, imageUrl: result.imageUrl, scope: 'user', updatedAt: Date.now() }
	safeSetStorage(ACTIVE_AVATAR_KEY, payload)
	tip('已保存，将返回聊天', { type: 'success' })
	setTimeout(() => uni.navigateBack(), 200)
}

let _videoPollTimer = null
function stopVideoPoll() {
	if (_videoPollTimer) {
		clearTimeout(_videoPollTimer)
		_videoPollTimer = null
	}
}

// 离开页面时清理轮询，避免后台继续请求
onHide(() => {
	stopVideoPoll()
})

onUnload(() => {
	stopVideoPoll()
})

let _videoPollStartedAt = 0
let _videoPollDelayMs = 1500

function persistVideoJob() {
	if (!video.jobId) {
		try {
			uni.removeStorageSync(VIDEO_JOB_KEY)
		} catch (e) {}
		return
	}
	try {
		uni.setStorageSync(VIDEO_JOB_KEY, {
			jobId: video.jobId,
			imageUrl: result.imageUrl,
			createdAt: Date.now(),
		})
	} catch (e) {}
}

function clearVideoJobPersisted() {
	try {
		uni.removeStorageSync(VIDEO_JOB_KEY)
	} catch (e) {}
}

function resumeVideoJobIfNeeded() {
	if (video.videoUrl) return
	if (video.jobId) {
		pollVideoStatus(video.jobId)
		return
	}
	let saved = null
	try {
		saved = uni.getStorageSync(VIDEO_JOB_KEY)
	} catch (e) {
		saved = null
	}
	if (!saved || typeof saved !== 'object') return
	if (saved.imageUrl && result.imageUrl && String(saved.imageUrl) !== String(result.imageUrl)) {
		// 头像已变化，不恢复旧任务
		clearVideoJobPersisted()
		return
	}
	if (saved.jobId) {
		video.jobId = String(saved.jobId)
		video.status = 'pending'
		pollVideoStatus(video.jobId)
	}
}

function isJobTimeout() {
	return _videoPollStartedAt && Date.now() - _videoPollStartedAt > 5 * 60 * 1000
}

function scheduleNextPoll(jobId) {
	_videoPollDelayMs = Math.min(Math.round(_videoPollDelayMs * 1.25), 3000)
	_videoPollTimer = setTimeout(() => pollVideoStatus(jobId), _videoPollDelayMs)
}

async function pollVideoStatus(jobId) {
	stopVideoPoll()
	if (!jobId) return
	if (!_videoPollStartedAt) {
		_videoPollStartedAt = Date.now()
		_videoPollDelayMs = 1500
	}
	if (isJobTimeout()) {
		tip('视频生成超时，请稍后重试')
		video.status = 'timeout'
		persistVideoJob()
		return
	}
	try {
		const res = await apiAvatarVideoStatus(jobId, 'user')
		const data = res?.data || {}
		video.status = String(data.status || '')
		const url = data.videoUrl
		if (url) {
			video.videoUrl = String(url)
			video.videoError = false
			video.status = 'succeeded'
			clearVideoJobPersisted()
			saveDraft()
			tip('视频生成成功', { type: 'success' })
			return
		}
		persistVideoJob()
		scheduleNextPoll(jobId)
	} catch (err) {
		const status = Number(err?.status || err?.statusCode)
		if (status === 404) {
			tip('任务不存在/已切换账号，已为你清理旧任务')
			video.jobId = ''
			video.status = ''
			clearVideoJobPersisted()
			saveDraft()
			return
		}
		if (status === 502) {
			tip('生成服务繁忙，稍后重试')
		}
		persistVideoJob()
		scheduleNextPoll(jobId)
	}
}

async function onGenerateVideo() {
	if (!canGenerateVideo.value) return tip('请先生成形象')
	loading.video = true
	try {
		stopVideoPoll()
		_videoPollStartedAt = 0
		_videoPollDelayMs = 1500
		video.videoUrl = ''
		video.videoError = false
		video.status = 'pending'
		video.jobId = ''

		const imageUrl = toApiFileUrl(result.imageUrl)
		if (!imageUrl || !String(imageUrl).startsWith('/files/')) {
			throw new Error('imageUrl must start with /files/')
		}
		const payload = { imageUrl, prompt: video.prompt?.trim() || undefined }
		const res = await apiAvatarVideoGenerateByImage(payload, 'user')
		const jobId = res?.data?.jobId
		if (!jobId) throw new Error('未返回 jobId')
		video.jobId = String(jobId)
		persistVideoJob()
		saveDraft()
		pollVideoStatus(video.jobId)
	} catch (err) {
		const msg = err?.message || err?.data?.detail || err?.data?.message || '生成视频失败'
		if (Number(err?.status) === 401) {
			tip('登录已过期，请重新登录')
			setTimeout(() => goLogin(), 200)
			return
		}
		tip(msg)
	} finally {
		loading.video = false
	}
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	padding: 18px 16px;
	padding-bottom: calc(18px + env(safe-area-inset-bottom));
	box-sizing: border-box;
	overflow-x: hidden;
	background:
		radial-gradient(900rpx 520rpx at 15% 8%, rgba(102, 217, 232, 0.26), transparent 60%),
		radial-gradient(860rpx 520rpx at 85% 16%, rgba(78, 205, 196, 0.22), transparent 58%),
		linear-gradient(180deg, rgba(255, 255, 255, 1) 0%, rgba(245, 251, 251, 1) 55%, rgba(255, 255, 255, 1) 100%);
}

.hd {
	text-align: center;
	padding: 10px 6px 12px;
}

.title {
	text-align: center;
	font-size: 20px;
	font-weight: 900;
	color: #1b1f2a;
	padding: 8px 6px 6px;
}

.sub {
	text-align: center;
	font-size: 13px;
	color: rgba(27, 31, 42, 0.55);
	padding: 0 6px;
}

.card {
	background: rgba(255, 255, 255, 0.92);
	border: 1px solid rgba(27, 31, 42, 0.08);
	border-radius: 18px;
	padding: 14px;
	box-shadow: 0 22px 42px rgba(20, 27, 61, 0.12);
}

.card-title {
	font-size: 16px;
	font-weight: 900;
	color: #1b1f2a;
}

.card-sub {
	margin-top: 6px;
	font-size: 13px;
	color: rgba(27, 31, 42, 0.55);
}

.stepbar {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: 10px;
	padding-bottom: 12px;
	border-bottom: 1px solid rgba(27, 31, 42, 0.06);
}

.step {
	font-size: 12px;
	font-weight: 800;
	color: rgba(27, 31, 42, 0.55);
}

.step-title {
	font-size: 14px;
	font-weight: 900;
	color: #1b1f2a;
}

.section {
	padding-top: 12px;
}

.hint {
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
	line-height: 18px;
}

.btn-row {
	margin-top: 12px;
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 10px;
}

.preview {
	margin-top: 12px;
	border-radius: 16px;
	overflow: hidden;
	border: 1px solid rgba(27, 31, 42, 0.08);
	background: rgba(255, 255, 255, 0.85);
}

.preview-img {
	width: 100%;
	height: 240px;
}

.preview-meta {
	padding: 10px 10px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.loading-card {
	margin-top: 12px;
	border-radius: 16px;
	border: 1px solid rgba(27, 31, 42, 0.08);
	background: rgba(255, 255, 255, 0.9);
	padding: 12px;
	display: flex;
	align-items: center;
	gap: 10px;
}

.loading-left {
	width: 34px;
	height: 34px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.loading-right {
	flex: 1;
	min-width: 0;
}

.loading-title {
	font-size: 13px;
	font-weight: 900;
	color: #1b1f2a;
}

.loading-sub {
	margin-top: 2px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
	line-height: 18px;
}

.video-loading-row {
	margin-top: 8px;
	display: flex;
	align-items: center;
	gap: 8px;
}

.video-loading-text {
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.spinner {
	width: 22px;
	height: 22px;
	border-radius: 50%;
	border: 2px solid rgba(78, 205, 196, 0.25);
	border-top-color: rgba(78, 205, 196, 1);
	animation: spin 0.9s linear infinite;
}

.spinner-sm {
	width: 16px;
	height: 16px;
	border-width: 2px;
}

@keyframes spin {
	0% {
		transform: rotate(0deg);
	}
	100% {
		transform: rotate(360deg);
	}
}

.field {
	margin-top: 12px;
}

.label {
	font-size: 13px;
	font-weight: 800;
	color: rgba(27, 31, 42, 0.75);
	margin-bottom: 8px;
}

.chips {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-bottom: 10px;
}

.chip {
	padding: 7px 10px;
	border-radius: 999px;
	background: rgba(102, 217, 232, 0.10);
	border: 1px solid rgba(102, 217, 232, 0.22);
	font-size: 12px;
	font-weight: 800;
	color: rgba(27, 31, 42, 0.75);
}

.chip.on {
	background: linear-gradient(180deg, rgba(102, 217, 232, 0.95) 0%, rgba(78, 205, 196, 0.95) 100%);
	border: none;
	color: #ffffff;
}

.voice-list {
	margin-top: 12px;
	display: grid;
	gap: 10px;
}

.voice-item {
	padding: 12px 12px;
	border-radius: 16px;
	border: 1px solid rgba(27, 31, 42, 0.08);
	background: rgba(255, 255, 255, 0.85);
}

.voice-item.on {
	border-color: rgba(78, 205, 196, 0.42);
	box-shadow: 0 16px 30px rgba(78, 205, 196, .14);
}

.voice-name {
	font-size: 14px;
	font-weight: 900;
	color: #1b1f2a;
}

.voice-sub {
	margin-top: 4px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.seg {
	margin-top: 4px;
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 8px;
	padding: 6px;
	border-radius: 14px;
	background: rgba(102, 217, 232, 0.10);
	border: 1px solid rgba(27, 31, 42, 0.06);
}

.seg-item {
	text-align: center;
	padding: 10px 8px;
	border-radius: 12px;
	font-size: 13px;
	font-weight: 900;
	color: rgba(27, 31, 42, 0.65);
}

.seg-item.on {
	background: rgba(255, 255, 255, 0.92);
	color: rgba(27, 31, 42, 0.90);
	box-shadow: 0 12px 22px rgba(20, 27, 61, 0.10);
}

.record-card {
	margin-top: 12px;
	padding: 12px;
	border-radius: 16px;
	border: 1px solid rgba(27, 31, 42, 0.08);
	background: rgba(255, 255, 255, 0.85);
}

.record-card.recording {
	border-color: rgba(255, 107, 107, 0.35);
}

.record-title {
	font-size: 14px;
	font-weight: 900;
	color: #1b1f2a;
}

.record-sub {
	margin-top: 6px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.record-meta {
	margin-top: 8px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.summary {
	margin-top: 4px;
	padding: 10px;
	border-radius: 16px;
	background: rgba(102, 217, 232, 0.08);
	border: 1px solid rgba(27, 31, 42, 0.06);
}

.sum-row {
	display: flex;
	justify-content: space-between;
	padding: 6px 4px;
}

.k {
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.v {
	font-size: 12px;
	font-weight: 800;
	color: rgba(27, 31, 42, 0.75);
}

.video-card {
	margin-top: 14px;
	padding: 12px;
	border-radius: 16px;
	border: 1px solid rgba(27, 31, 42, 0.08);
	background: rgba(255, 255, 255, 0.85);
}

.video-title {
	font-size: 14px;
	font-weight: 900;
	color: #1b1f2a;
}

.video-meta {
	margin-top: 8px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.video-preview {
	margin-top: 10px;
	border-radius: 14px;
	overflow: hidden;
	border: 1px solid rgba(27, 31, 42, 0.08);
}

.video {
	width: 100%;
	height: 220px;
	background: #000;
}

.actions {
	margin-top: 14px;
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 10px;
}

.draft-actions {
	margin-top: 10px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
}

.draft-tip {
	font-size: 12px;
	color: rgba(27, 31, 42, 0.45);
}

.draft-clear {
	font-size: 12px;
	font-weight: 800;
	color: rgba(255, 107, 107, 0.95);
}
</style>
