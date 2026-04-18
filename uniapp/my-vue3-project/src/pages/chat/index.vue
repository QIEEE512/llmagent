<template>
    <!-- 页面根容器 -->
    <view class="page">
        <!-- 自定义顶部导航栏（非原生） -->
        <view class="top" :style="topStyle">
            <view class="top-inner">
                <!-- 左侧：返回历史记录 -->
                <view class="top-left" @tap="goHistory">
                    <u-icon name="list" size="22" :color="palette.icon" />
                </view>

                <!-- 中间标题 -->
                <view class="top-title">
                    <view class="top-title-text">超级AI智能</view>
                    <view v-if="activeAvatar?.imageUrl" class="top-avatar" aria-label="当前数字人">
                        <image class="top-avatar-img" :src="toDisplayUrl(activeAvatar.imageUrl)" mode="aspectFill" />
                    </view>
                </view>

                <!-- 右侧操作区 -->
                <view class="top-actions">
                    <!-- 定制数字人入口 -->
                    <view class="top-action" @tap="goAvatarCustomizer" aria-label="定制数字人">
                        <view class="orb" aria-hidden="true"></view> <!-- 视觉装饰小圆点 -->
                    </view>

                    <!-- 更多菜单（账号/设置） -->
                    <view class="top-action" @tap="openMore" aria-label="更多">
                        <u-icon name="more-dot-fill" size="22" :color="palette.icon" />
                    </view>
                </view>
            </view>
        </view>

        <!-- 可滚动内容区 -->
        <scroll-view class="body" scroll-y :scroll-with-animation="true" :scroll-into-view="scrollIntoId" :style="bodyStyle">
            <!-- 英雄区域：欢迎语 + Logo -->
            <view class="hero">
                <view class="hero-logo">
                    <view class="logo-ring"></view>   <!-- 外环 -->
                    <view class="logo-core">   <!-- 内核 -->
                        <image v-if="activeAvatar?.imageUrl" class="logo-avatar" :src="toDisplayUrl(activeAvatar.imageUrl)" mode="aspectFill" />
                    </view>
                </view>
                <view class="hero-title">Hi，<text class="hero-strong">我是你的AI朋友！</text></view>
                <view class="hero-sub">左上角点击查看历史档案</view>
            </view>

            <!-- 聊天消息区 -->
            <view class="chat-area" ref="chatArea">
                <view v-for="msg in messages" :key="msg.id" :id="'msg-'+msg.id" class="chat-msg" :class="msg.role">
                    <view class="bubble" :class="{ pending: !!msg.pending }">{{ msg.text }}</view>
                </view>
            </view>

            <!-- 推荐问题卡片 -->
            <view v-if="showCard" class="card-wrap">
                <u-card :border="false" :margin="'0'" :padding="'0'" :round="18" class="card">
                    <template #body>
                        <!-- 卡片头部 -->
                        <view class="card-hd">
                            <view class="card-title">今天学点啥？</view>
                        </view>

                        <!-- 推荐问题列表 -->
                        <view class="q-list">
                            <view
                                v-for="item in questions"
                                :key="item.id"
                                class="q-item"
                                @tap="pick(item.text)"
                            >
                                <view class="q-quote" aria-hidden="true">“</view>
                                <view class="q-text">{{ item.text }}</view>
                                <view class="q-go"><u-icon name="arrow-right" size="16" :color="palette.muted" /></view>
                            </view>
                        </view>

                        <!-- 底部：换一换按钮 -->
                        <view class="card-ft">
                            <u-button
                                type="primary"
                                shape="circle"
                                :size="'small'"
                                :loading="loading.shuffle"
                                :customStyle="shuffleBtnStyle"
                                @tap="shuffle"
                            >
                                <u-icon name="reload" size="16" color="#ffffff" />
                                <text class="shuffle-text">换一换</text>
                            </u-button>
                        </view>
                    </template>
                </u-card>
            </view>

            <!-- 待发送附件预览（有附件时显示） -->
            <view v-if="pendingAttachments.length" class="attach-strip">
                <view v-for="att in pendingAttachments" :key="att.id" class="attach-chip" :class="att.type">
                    <!-- 图片：用一个超微型缩略图作为“上传成功可视化” -->
                    <image
                        v-if="att.type==='image' && att.url"
                        class="attach-thumb"
                        :src="toDisplayUrl(att.url)"
                        mode="aspectFill"
                    />
                    <u-icon v-else-if="att.type==='image'" name="photo" size="16" :color="palette.primary" />
                    <u-icon v-else name="file-text" size="16" :color="palette.primary" />
                    <text class="attach-chip-text">{{ att.name || (att.type==='image' ? '图片' : '文件') }}</text>
                    <view class="attach-chip-x" @tap="removeAttachment(att.id)">
                        <u-icon name="close" size="14" :color="palette.muted" />
                    </view>
                </view>
                <view class="attach-hint" v-if="pendingAttachments.some(a => a.type === 'image')">
                    仅支持本服务上传返回的 /files/ 图片进行识别
                </view>
            </view>

            <!-- 底部留白，避免被输入框遮挡 -->
            <view class="spacer"></view>
        </scroll-view>

        <!-- 底部输入工具栏 -->
        <view class="composer" :style="composerStyle">
            <view class="composer-inner">
                <!-- 相机按钮 -->
                <u-button
                    class="icon-btn"
                    type="default"
                    shape="circle"
                    :customStyle="iconBtnStyle"
                    :loading="loading.camera"
                    @tap="onCamera"
                >
                    <u-icon name="camera" size="22" :color="palette.primary" />
                </u-button>

                <!-- 文件上传 -->
                <u-button
                    class="icon-btn"
                    type="default"
                    shape="circle"
                    :customStyle="iconBtnStyle"
                    :loading="loading.file"
                    @tap="onFile"
                >
                    <u-icon name="file-text" size="22" :color="palette.primary" />
                </u-button>

                <!-- 文本输入框 -->
                <view class="input-wrap">
                    <!-- 语音模式：按住说话 -->
                    <view v-if="voiceMode" class="hold-to-talk" :class="{ 'is-recording': voiceRecording }">
                        <view
                            class="hold-btn"
                            @touchstart.prevent.stop="onHoldStart"
                            @touchend.prevent.stop="onHoldEnd"
                            @touchcancel.prevent.stop="onHoldCancel"
                        >
                            {{ voiceRecording ? '松开结束' : '按住说话' }}
                        </view>
                    </view>

                    <!-- 文本模式：输入框 -->
                    <u-input
                        v-else
                        v-model="input"
                        type="textarea"
                        autoHeight
                        :maxlength="200"
                        :showConfirmBar="false"
                        confirmType="send"
                        placeholder="请输入问题"
                        clearable
                        border="none"
                        :customStyle="inputStyle"
                        @confirm="onSend"
                    />
                </view>

                <!-- 语音输入 -->
                <u-button
                    class="icon-btn"
                    type="default"
                    shape="circle"
                    :customStyle="iconBtnStyle"
                    :loading="loading.voice"
                    @tap="toggleVoiceMode"
                >
                    <!-- uview-plus 在部分版本/字体库里没有 keyboard 图标，会回退显示英文；这里用已验证存在的 edit-pen 作为“切回输入”的替代 -->
                    <u-icon :name="voiceMode ? 'edit-pen' : 'mic'" size="22" :color="palette.primary" />
                </u-button>

                <!-- 发送按钮（仅当有内容时可点击） -->
                <u-button
                    class="icon-btn"
                    type="primary"
                    shape="circle"
                    :customStyle="sendBtnStyle"
                    :loading="loading.send"
                    :disabled="!canSend"
                    @tap="onSend"
                >
                    <u-icon name="arrow-upward" size="22" color="#ffffff" />
                </u-button>
            </view>
        </view>

        <!-- 全局轻提示 -->
        <u-toast ref="toastRef" />

        <!-- 录音确认弹窗 -->
        <u-popup :show="voiceConfirmVisible" mode="center" @close="voiceConfirmVisible = false">
            <view class="voice-confirm">
                <view class="voice-confirm-title">发送语音？</view>
                <view class="voice-confirm-sub">松开后可选择发送或取消</view>
                <view class="voice-confirm-actions">
                    <u-button type="default" @tap="onVoiceCancelSend">取消</u-button>
                    <u-button type="primary" :loading="loading.voice" @tap="onVoiceSend">发送</u-button>
                </view>
            </view>
        </u-popup>
    </view>
</template>

<script setup>
// Vue 响应式工具
import { computed, ref, nextTick, watch } from 'vue'

// uni-app 生命周期
import { onShow, onLoad } from '@dcloudio/uni-app'

// 本地存储：获取登录状态
import { getToken } from '@/services/storage'

// 预留的 API 接口（需你实现）
import {
    apiGetRecommendations,
    apiUploadChatImage,
    apiUploadChatFile,
    apiAsr,
    apiChat,
    apiUploadVoice,
    apiVoiceChat,
    apiGetConversation,
    apiCreateNewConversation,
    apiAppendConversationMessage,
    apiGetActiveAvatar,
} from '@/services/api'

// 当前后端 /api/chat 已做会话落库时，需关闭前端手动 append，避免一条消息被写两次。
const ENABLE_MANUAL_CONVERSATION_APPEND = false

// 主题色配置（蓝绿色系，柔和专业）
const palette = {
    primary: '#4ECDC4',      // 主色
    primary2: '#66D9E8',     // 辅助色
    text: '#1B1F2A',         // 主文字
    muted: 'rgba(27,31,42,.45)', // 次要文字
    card: 'rgba(255,255,255,.92)',
    icon: 'rgba(27,31,42,.70)',  // 图标颜色
}

// 引用 Toast 组件
const toastRef = ref(null)

// 当前激活的数字人（来自 avatar-custom 保存）
const ACTIVE_AVATAR_KEY = 'active_avatar'
const activeAvatar = ref(null)

async function readActiveAvatar() {
    try {
        const res = await apiGetActiveAvatar('user')
        const data = res?.data || null
        if (data && (data.imageUrl || data.avatarId)) {
            activeAvatar.value = data
            try {
                uni.setStorageSync(ACTIVE_AVATAR_KEY, data)
            } catch (e) {
                // ignore cache failure
            }
            return
        }
    } catch (e) {
        // fallback to local cache
    }

    try {
        const v = uni.getStorageSync(ACTIVE_AVATAR_KEY)
        if (v && typeof v === 'object' && (v.imageUrl || v.avatarId)) {
            activeAvatar.value = v
        } else {
            activeAvatar.value = null
        }
    } catch (e) {
        activeAvatar.value = null
    }
}

// 用户输入内容
const input = ref('')
// 聊天消息列表（按时间顺序）
const messages = ref([])
// 用于 scroll-view 的滚动目标 id（绑定到 :scroll-into-view）
const scrollIntoId = ref('')

// 当前会话 id（用于多轮记忆）
const currentConversationId = ref(null)

// 进入聊天页时通过 query 读取 conversationId，并加载历史消息
onLoad((query) => {
    try {
        const cid = query?.conversationId
        currentConversationId.value = cid || null
    } catch (e) {
        currentConversationId.value = null
    }
})

async function ensureConversationId({ title } = {}) {
    if (currentConversationId.value) return currentConversationId.value
    const res = await apiCreateNewConversation({ title: title || '' })
    const cid = res?.data?.conversationId
    if (cid) currentConversationId.value = cid
    return currentConversationId.value
}

function mapServerMessageToUi(m) {
    const id = m?.messageId || m?.id || `${m?.role || 'u'}-${Date.now()}`
    return {
        id,
        role: m?.role || 'assistant',
        text: m?.text || '',
        pending: false,
    }
}

async function loadConversationIfNeeded() {
    if (!currentConversationId.value) {
        // 新对话：清空 UI
        messages.value = []
        showCard.value = true
        return
    }
    try {
        const res = await apiGetConversation(currentConversationId.value)
        const data = res?.data || {}
        const list = Array.isArray(data?.messages) ? data.messages : []
        messages.value = list.map(mapServerMessageToUi)
        showCard.value = messages.value.length === 0
        await nextTick()
    } catch (e) {
        console.error('[conversation] load error', e)
        // 加载失败不阻塞输入
    }
}

// 监听 messages 的变化，自动滚动到最后一条消息
watch(messages, (list) => {
    const last = list && list.length ? list[list.length - 1] : null
    if (last && last.id) {
        // 设置 scrollIntoId 为最后消息的 DOM id（模板中 id='msg-'+msg.id）
        scrollIntoId.value = `msg-${last.id}`
    }
}, { deep: true, flush: 'post' })
// 是否显示“今天学点啥”推荐卡片
const showCard = ref(true)

// 各操作加载状态（相机、文件、语音、换一换、发送）
const loading = ref({ camera: false, file: false, voice: false, shuffle: false, send: false })

// 语音输入模式（类似微信）：true=按住说话；false=键盘输入
const voiceMode = ref(false)
const voiceRecording = ref(false)
const voiceConfirmVisible = ref(false)
const lastVoiceFilePath = ref('')
const lastSendFingerprint = ref('')
const lastSendAt = ref(0)

// 录音实例句柄（用于“按下 start、松开 stop”）
const _activeRecorder = ref(null)
const _activeRecorderStopHandler = ref(null)
const _activeRecorderErrorHandler = ref(null)

// 是否可发送（输入非空）
const canSend = computed(() => input.value.trim().length > 0)

// 本地推荐问题池（分组轮播）
const pool = [
    ['人为什么会犯困？有什么科学解释？', '我想练英语口语，从哪里开始最好？', '帮我用儿童能懂的方式解释“电”是什么。'],
    ['今天我数学有点卡，能教我分数吗？', '怎么制定一个不累的学习计划？', '给我 3 个有趣的科学小实验（安全可在家做）。'],
    ['我想写作文，但不知道怎么开头，能给灵感吗？', '为什么天空是蓝色的？', '背单词有什么记得牢的方法？'],
    ['讲讲恐龙为什么会灭绝（儿童版）。', '我想提高专注力，有哪些简单训练？', '如何把一篇课文讲得更有感情？'],
]

// 当前显示的问题列表
const questions = ref([])
let poolIndex = 0

// 初始化问题列表（从 pool 中取一组）
const mountQuestions = () => {
    const arr = pool[poolIndex % pool.length]
    questions.value = arr.map((t, i) => ({ id: `${poolIndex}-${i}`, text: t }))
}
mountQuestions()

// 进入/返回页面时刷新当前数字人
try {
    // 若已在文件顶部引入 onShow，这里会正常工作；否则不影响运行（仅 try/catch）
    onShow(async () => {
        await readActiveAvatar()
        loadConversationIfNeeded()
    })
} catch (e) {
    // ignore
}

// 首次加载也读一次
readActiveAvatar()

// 顶部导航栏样式：适配状态栏高度（刘海屏/挖孔屏）
const topStyle = computed(() => {
    const top = (uni.getSystemInfoSync?.().statusBarHeight || 0) + 'px'
    return `padding-top:${top};`
})

// 底部输入栏样式：适配 iPhone X 等机型的安全区域
const composerStyle = computed(() => {
    const bottom = uni.getSystemInfoSync?.().safeAreaInsets?.bottom || 0
    return bottom ? `padding-bottom:${bottom}px;` : ''
})

// 通用图标按钮样式（相机/文件/语音）
const iconBtnStyle = {
    // 稍微缩小按钮，给输入框多腾一点横向空间
    width: '40px',
    height: '40px',
    padding: '0',
    background: 'rgba(255,255,255,.85)',
    borderWidth: '1px',
    borderColor: 'rgba(27,31,42,.08)',
    borderRadius: '999px',
    boxShadow: '0 10px 26px rgba(20, 27, 61, .10)',
}

// 发送按钮样式（渐变 + 无边框）
const sendBtnStyle = {
    ...iconBtnStyle,
    background: 'linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%)',
    borderWidth: '0',
}

// 换一换按钮样式
const shuffleBtnStyle = {
    background: 'linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%)',
    border: 'none',
    padding: '0 14px',
    height: '36px',
    boxShadow: '0 16px 30px rgba(78, 205, 196, .22)',
    fontWeight: '800',
}

// 输入框样式
const inputStyle = {
    fontSize: '16px',
    padding: '10px 12px',
    color: palette.text,
    lineHeight: '22px',
    minHeight: '22px',
    // 确保不截断：允许换行显示
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
}

// 根据输入内容行数动态估算 composer 高度，给 scroll-view 预留底部空间
const composerExtra = computed(() => {
    // 估算：首行 44px（按钮行基线）+ 每增加一行约 22px，并做上下限控制
    // input 200 字以内：这里用字符数粗略推行数（不做精确测量，避免影响其它布局）
    const chars = (input.value || '').length
    const approxLines = Math.min(6, Math.max(1, Math.ceil(chars / 20)))
    const extra = (approxLines - 1) * 22
    return Math.min(110, Math.max(0, extra))
})

// scroll-view 高度与底部留白随 composer 高度变化
const bodyStyle = computed(() => {
    // top 52px 已在 .body 的 calc 里扣掉，这里只做 padding-bottom 的动态增强
    // 180 为原本留白基准；根据输入框增长额外增加
    const base = 180
    const pb = base + composerExtra.value
    return `padding-bottom:${pb}px;`
})

// 封装 Toast 提示（统一样式）
// uview-plus 的 u-toast 支持通过 show({ message, type, duration, position, offset }) 控制展示样式。
// 注意：不同版本字段可能略有差异，但 message/type/duration 在多数版本可用。
function tip(msg, options = {}) {
    const {
        type = 'default', // default | success | error | warning | loading
        duration = 1800,
        position = 'bottom',
        offset = 90,
    } = options || {}

    toastRef.value?.show({
        message: msg,
        type,
        duration,
        position,
        offset,
    })
}

function getExtFromPath(p) {
    const s = String(p || '').split('?')[0].split('#')[0]
    const last = s.split(/[\\/]/).pop() || ''
    const ext = last.includes('.') ? last.split('.').pop() : ''
    return String(ext || '').toLowerCase()
}

async function statLocalFile(filePath) {
    // 统一拿到 size（若取不到也不阻塞，只用于排查与前端兜底）
    return await new Promise((resolve) => {
        try {
            uni.getFileInfo({
                filePath,
                success: (res) => resolve({ ok: true, size: res?.size }),
                fail: (err) => resolve({ ok: false, err }),
            })
        } catch (e) {
            resolve({ ok: false, err: e })
        }
    })
}

// 点击推荐问题：填充到输入框
function pick(text) {
    input.value = text
    tip('已填充到输入框', { type: 'success' })
}

// 通用加载包装器：自动管理 loading 状态
async function withLoading(key, fn) {
    loading.value[key] = true
    try {
        await fn()
    } finally {
        loading.value[key] = false
    }
}

/**
 * =========================
 * 后端接口预留说明（占位函数）
 * 实际开发时，请在 '@/services/api' 中实现：
 * - apiGetRecommendations(): 获取推荐问题
 * - apiUploadChatImage(): 上传图片
 * - apiUploadChatFile(): 上传文件
 * - apiAsr(): 语音转文字
 * - apiChat(): 发送对话
 * =========================
 */

// 统一错误处理
function showError(err, fallback) {
    const msg = err?.message || err?.data?.detail || err?.data?.message || fallback || '请求失败'
    tip(msg, { type: 'error', duration: 2500 })
}

function toDisplayUrl(url) {
    // 后端返回通常是 /files/xxx.png（相对路径），这里拼上域名，H5 才能显示缩略图。
    // 开发态在 localhost 下展示也需要绝对路径，否则会请求到 Vite 站点。
    if (!url) return ''
    if (/^https?:\/\//i.test(url)) return url
    try {
        // 与 http.js 中 API_ORIGIN 保持一致（避免循环依赖，这里重复常量）
        const API_ORIGIN = 'https://jkyhobdhqqah.sealoshzh.site'
        return API_ORIGIN + url
    } catch (e) {
        return url
    }
}

// 获取推荐问题（可替换为真实 API）
async function apiFetchRecommendations() {
    // 后端接口是可选能力：如果后端尚未实现 /api/recommendations，这里会抛错
    // 上层 shuffle() 会捕获并回退到本地问题池，避免影响“换一换”体验。
    const res = await apiGetRecommendations()
    return res?.data?.items || []
}

// 上传图片（返回 URL）
async function apiUploadImage(tempFilePath) {
    // 后端返回 ApiResponse: { ok, code, message, data: { url, name, size, mime } }
    // 这里保留完整结构，交由 normalizeUploadedToAttachment 统一解析
    const res = await apiUploadChatImage(tempFilePath)
    return res
}

// 上传文件
async function apiUploadFile(filePath) {
    // 保留完整 ApiResponse 结构
    const res = await apiUploadChatFile(filePath)
    return res
}

// 语音识别（ASR）
// 保留：如果后端仍提供 /api/asr，可走“语音->文字”模式
async function apiSpeechToText(audioUrl) {
    const res = await apiAsr({ audioUrl })
    return res?.data || { text: '' }
}

// 录音：优先 App 原生 plus.audio.getRecorder，其次跨端 RecorderManager
function recordOnce({ durationMs = 15000 } = {}) {
    return new Promise((resolve, reject) => {
        // #ifdef APP-PLUS
        try {
            const recorder = plus?.audio?.getRecorder?.()
            if (recorder) {
                recorder.record(
                    {
                        filename: '_doc/voice/',
                        format: 'aac',
                    },
                    (path) => resolve({ filePath: path }),
                    (e) => reject(e)
                )
                // 超时自动停止
                setTimeout(() => {
                    try { recorder.stop() } catch (e) { /* ignore */ }
                }, durationMs)
                return
            }
        } catch (e) {
            // fallback to recorderManager
        }
        // #endif

        // #ifndef APP-PLUS
        // 其它端（含 H5/小程序）
        // #endif
        try {
            const rm = uni.getRecorderManager?.()
            if (!rm) return reject(new Error('当前端不支持录音'))

            let done = false
            const cleanup = () => {
                try { rm.offStop && rm.offStop(onStop) } catch (e) { /* ignore */ }
                try { rm.offError && rm.offError(onError) } catch (e) { /* ignore */ }
            }
            const onStop = (res) => {
                if (done) return
                done = true
                cleanup()
                const filePath = res?.tempFilePath
                if (!filePath) return reject(new Error('录音失败：未生成音频文件'))
                resolve({ filePath })
            }
            const onError = (err) => {
                if (done) return
                done = true
                cleanup()
                reject(err)
            }

            rm.onStop(onStop)
            rm.onError(onError)
            rm.start({ duration: durationMs, format: 'aac' })

            // 兜底：到时间主动 stop（部分端 duration 不稳定）
            setTimeout(() => {
                try { rm.stop() } catch (e) { /* ignore */ }
            }, durationMs)
        } catch (e) {
            reject(e)
        }
    })
}

/**
 * 真·按住说话：按下 start / 松开 stop
 * - APP-PLUS: plus.audio.getRecorder().record(...) + stop()
 * - 其它端: uni.getRecorderManager().start(...) + stop()
 * 注意：H5 对录音能力支持差异较大，若失败会提示。
 */
function startHoldRecord({ maxDurationMs = 60000 } = {}) {
    return new Promise((resolve, reject) => {
        // 防重复
        if (_activeRecorder.value) {
            return reject(new Error('录音中'))
        }

        // #ifdef APP-PLUS
        try {
            const recorder = plus?.audio?.getRecorder?.()
            if (!recorder) {
                // fallthrough
            } else {
                _activeRecorder.value = { kind: 'plus', recorder }
                recorder.record(
                    {
                        filename: '_doc/voice/',
                        format: 'aac',
                    },
                    (path) => {
                        // stop 后回调
                        _activeRecorder.value = null
                        resolve({ filePath: path })
                    },
                    (e) => {
                        _activeRecorder.value = null
                        reject(e)
                    }
                )

                // 超时兜底（不建议太短，微信按住可能较久；这里给 60s）
                setTimeout(() => {
                    try { stopHoldRecord() } catch (e) { /* ignore */ }
                }, maxDurationMs)
                return
            }
        } catch (e) {
            // fallback to recorderManager
        }
        // #endif

        try {
            const rm = uni.getRecorderManager?.()
            if (!rm) return reject(new Error('当前端不支持录音'))

            const onStop = (res) => {
                cleanup()
                const filePath = res?.tempFilePath
                if (!filePath) return reject(new Error('录音失败：未生成音频文件'))
                resolve({ filePath })
            }
            const onError = (err) => {
                cleanup()
                reject(err)
            }
            const cleanup = () => {
                try { rm.offStop && rm.offStop(onStop) } catch (e) { /* ignore */ }
                try { rm.offError && rm.offError(onError) } catch (e) { /* ignore */ }
                _activeRecorder.value = null
                _activeRecorderStopHandler.value = null
                _activeRecorderErrorHandler.value = null
            }

            _activeRecorder.value = { kind: 'uni', recorder: rm }
            _activeRecorderStopHandler.value = onStop
            _activeRecorderErrorHandler.value = onError
            rm.onStop(onStop)
            rm.onError(onError)
            rm.start({ duration: maxDurationMs, format: 'aac' })

            // 兜底：到时间主动 stop（部分端 duration 不稳定）
            setTimeout(() => {
                try { stopHoldRecord() } catch (e) { /* ignore */ }
            }, maxDurationMs)
        } catch (e) {
            _activeRecorder.value = null
            reject(e)
        }
    })
}

function stopHoldRecord() {
    const h = _activeRecorder.value
    if (!h) return
    if (h.kind === 'plus') {
        try { h.recorder.stop() } catch (e) { /* ignore */ }
        return
    }
    try { h.recorder.stop() } catch (e) { /* ignore */ }
}

// 发送聊天消息
async function apiSendChat(payload) {
    const res = await apiChat(payload)
    return res?.data
}

// “换一换”按钮逻辑
function shuffle() {
    return withLoading('shuffle', async () => {
        // 默认使用本地推荐问题池（分组轮播），不依赖后端接口。
        // 若后端实现了 recommendations，则可在不影响体验的前提下“有则用之”。
        poolIndex++

        // 先本地轮播，保证立即有反馈
        mountQuestions()

        // 可选：尝试用后端数据覆盖（失败/404 不提示，不打断）
        try {
            const items = await apiFetchRecommendations()
            if (Array.isArray(items) && items.length > 0) {
                questions.value = items.map((it, i) => ({ id: it.id || `${Date.now()}-${i}`, text: it.text }))
            }
        } catch (err) {
            // 静默：后端未实现或网络异常时，不提示 not found，继续使用本地池
            console.log('[recommendations] fallback to local pool:', err?.status || err?.statusCode || err)
        }
    })
}

// 导航：历史记录
function goHistory() {
    uni.navigateTo({ url: '/pages/history/index' })
}

// 导航：数字人定制
function goAvatarCustomizer() {
    uni.navigateTo({ url: '/pages/avatar-custom/index' })
}

// 导航：更多（设置/账号）
function openMore() {
    uni.navigateTo({ url: '/pages/more/index' })
}

// 相机功能
function onCamera() {
    return withLoading('camera', async () => {
        try {
            const choose = await new Promise((resolve, reject) => {
                uni.chooseImage({ count: 1, success: resolve, fail: reject })
            })
            const tempFilePath = choose?.tempFilePaths?.[0]
            if (!tempFilePath) return tip('未选择图片')

            const uploadedRes = await apiUploadImage(tempFilePath)
            console.log('[upload:image] response', uploadedRes)
            const up = normalizeUploadedToAttachment(uploadedRes, { name: '图片' })
            if (!up.url) return tip('图片上传失败：服务器未返回图片地址')
            if (!isBackendFilesUrl(up.url)) {
                return tip('图片上传成功，但地址不可用于识别（需返回 /files/ 开头的地址）')
            }

            pendingAttachments.value.push({
                id: `att-${Date.now()}`,
                type: 'image',
                ...up,
            })

            tip('图片已添加', { type: 'success' })
        } catch (err) {
            showError(err, '图片上传失败')
        }
    })
}

// 文件上传
function onFile() {
    return withLoading('file', async () => {
        try {
            // 仅允许常见文档（pdf/word/excel）
            const allowedExt = ['pdf', 'doc', 'docx', 'xls', 'xlsx']
            const allowedMime = [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ]

            // 统一选择文件：不同端 API 行为差异较大，这里做平台分支 + 超时兜底，避免 Promise 悬挂导致按钮一直转圈。
            const choose = await new Promise((resolve, reject) => {
                let done = false
                const finish = (fn, arg) => {
                    if (done) return
                    done = true
                    clearTimeout(tid)
                    fn(arg)
                }

                const tid = setTimeout(() => {
                    finish(reject, new Error('文件选择超时，请重试或检查权限'))
                }, 15000)

                // 先按平台选择更稳的 API
                const sys = uni.getSystemInfoSync?.() || {}
                const platform = String(sys.platform || '').toLowerCase()
                const isMp = typeof __wxjs_environment !== 'undefined' || platform === 'mp-weixin'
                const hasChooseFile = typeof uni.chooseFile === 'function'
                const hasChooseMessageFile = typeof uni.chooseMessageFile === 'function'

                console.log('[file:choose] sys', {
                    platform,
                    brand: sys.brand,
                    model: sys.model,
                    system: sys.system,
                    uniPlatform: sys.uniPlatform,
                    appWgtVersion: sys.appWgtVersion,
                    hasChooseFile,
                    hasChooseMessageFile,
                    isMp,
                    // 编译期宏：用于确认当前包的目标
                    APP: typeof APP_PLUS !== 'undefined' ? APP_PLUS : undefined,
                    H5: typeof H5 !== 'undefined' ? H5 : undefined,
                    MP: typeof MP !== 'undefined' ? MP : undefined,
                })

                const useChooseMessageFile = () => {
                    if (typeof uni.chooseMessageFile !== 'function') return false
                    uni.chooseMessageFile({
                        count: 1,
                        type: 'file',
                        success: (res) => finish(resolve, res),
                        fail: (err) => finish(reject, err),
                    })
                    return true
                }

                const useChooseFile = () => {
                    if (typeof uni.chooseFile !== 'function') return false
                    // 注意：部分端 chooseFile 可能不支持 extension 参数，失败时降级重试
                    try {
                        uni.chooseFile({
                            count: 1,
                            extension: allowedExt,
                            success: (res) => finish(resolve, res),
                            fail: (err) => {
                                // 降级：不带 extension 再试一次
                                try {
                                    uni.chooseFile({
                                        count: 1,
                                        success: (res2) => finish(resolve, res2),
                                        fail: (err2) => finish(reject, err2),
                                    })
                                } catch (e2) {
                                    finish(reject, err || e2)
                                }
                            },
                        })
                        return true
                    } catch (e) {
                        return false
                    }
                }

                // App-Plus：优先尝试使用 plus 原生能力打开系统文件选择器。
                // 说明：不同基座/运行时对 plus 的实现能力存在差异；如果这里不可用，会给出明确提示。
                const usePlusFilePicker = () => {
                    // #ifdef APP-PLUS
                    try {
                        if (typeof plus === 'undefined') return false

                        // 尝试区分常见实现：部分运行时提供 plus.io.chooseFile
                        if (plus?.io && typeof plus.io.chooseFile === 'function') {
                            plus.io.chooseFile(
                                {
                                    multiple: false,
                                    // 尽量限制为文档类型（实现是否生效取决于运行时）
                                    type: 'file',
                                    // 有的实现支持 extension（数组或逗号分隔字符串）
                                    extension: allowedExt,
                                },
                                (picked) => {
                                    // 不同实现返回值差异较大：可能是 string，也可能是 {files:["content://..."]}
                                    const uri =
                                        typeof picked === 'string'
                                            ? picked
                                            : (picked?.files && Array.isArray(picked.files) ? picked.files[0] : '')

                                    // 统一成与 chooseFile 类似的结构，并尽量补齐文件名（用于扩展名校验）
                                    const guessName = uri ? String(uri).split(/[\\/]/).pop() : ''
                                    finish(resolve, {
                                        tempFilePaths: uri ? [uri] : [],
                                        tempFiles: guessName ? [{ name: guessName, path: uri }] : undefined,
                                        __from: 'plus.io.chooseFile',
                                    })
                                },
                                (err) => finish(reject, err)
                            )
                            return true
                        }

                        // 若没有 chooseFile 能力，明确失败
                        return false
                    } catch (e) {
                        return false
                    }
                    // #endif
                    return false
                }

                // 小程序优先 chooseMessageFile；H5 优先 chooseFile；App-Plus 优先 plus 文件选择
                const started = isMp
                    ? (useChooseMessageFile() || useChooseFile())
                    : (useChooseFile() || usePlusFilePicker() || useChooseMessageFile())
                if (!started) {
                    const missing = []
                    if (!hasChooseFile) missing.push('uni.chooseFile')
                    if (!hasChooseMessageFile) missing.push('uni.chooseMessageFile')
                    const msg = `当前平台不支持选择文件：缺少 ${missing.join(' / ')}。` +
                        `这是 App 运行时能力限制：请确认用的是标准 App-Plus 基座/正式包，` +
                        `或集成支持系统文件选择器的能力（plus 文件选择 / 原生插件）。`
                    finish(reject, new Error(msg))
                }
            })

            // chooseFile: tempFilePaths；chooseMessageFile: tempFiles[].path
            const firstTempFile = choose?.tempFiles?.[0]
            const filePath = choose?.tempFilePaths?.[0] || firstTempFile?.path || firstTempFile?.tempFilePath
            const fileName = firstTempFile?.name || (filePath ? String(filePath).split(/[\\/]/).pop() : '')
            const fileSize = firstTempFile?.size
            const fileType = firstTempFile?.type
            if (!filePath) return tip('未选择文件')

            console.log('[file:selected]', {
                from: choose?.__from,
                filePath,
                fileName,
                fileType,
                fileSize,
                tempFiles0: firstTempFile,
            })

            // 二次校验扩展名 / mime（不同端返回字段不一致，这里尽量兜底）
            const safeTail = (s) => {
                const str = String(s || '')
                // 去掉 query / fragment，避免 content://xxx.pdf?foo 这种误判
                return str.split('?')[0].split('#')[0]
            }

            const hasContentUri = String(filePath || '').startsWith('content://')
            const extFromName = safeTail(fileName).split('.').pop()?.toLowerCase()
            const extFromPath = filePath ? safeTail(filePath).split('.').pop()?.toLowerCase() : ''
            const ext = extFromName || extFromPath
            const hasExt = Boolean(ext)
            // content:// 场景通常拿不到真实文件名/后缀，前端无法可靠拦截；交给后端按 mime/内容再校验
            const extOk = hasContentUri ? true : (hasExt ? allowedExt.includes(ext) : true)
            const mimeOk = fileType ? allowedMime.includes(fileType) : true

            console.log('[file:check]', { hasContentUri, extFromName, extFromPath, ext, hasExt, extOk, mimeOk })
            if (!extOk) {
                return tip('仅支持 PDF/Word/Excel 文件')
            }
            if (!mimeOk) {
                return tip('文件类型不支持（仅支持 PDF/Word/Excel）')
            }

            const uploadedRes = await apiUploadFile(filePath)
            const up = normalizeUploadedToAttachment(uploadedRes, { name: fileName || '文件', size: fileSize })
            if (!up.url) return tip('文件上传失败：服务器未返回文件地址')

            pendingAttachments.value.push({
                id: `att-${Date.now()}`,
                type: 'file',
                ...up,
            })

            tip('文件已添加', { type: 'success' })
        } catch (err) {
            showError(err, '文件上传失败')
        }
    })
}

// 语音输入（当前为占位）
function toggleVoiceMode() {
    // 录音中不允许切换
    if (voiceRecording.value) return
    voiceMode.value = !voiceMode.value
}

function onHoldStart() {
    if (loading.value.voice) return
    voiceRecording.value = true
    lastVoiceFilePath.value = ''
    // 这里不做“松手即发”，而是松手后弹出发送/取消
    tip('录音中…')
    // 关键：按下就开始录
    startHoldRecord({ maxDurationMs: 60000 })
        .then(async ({ filePath }) => {
            // stop 后回调会落在这里
            const ext = getExtFromPath(filePath)
            const info = await statLocalFile(filePath)
            console.log('[voice] recorded file', { filePath, ext, size: info?.size, statOk: info?.ok })

            // 经验值：< 1KB 几乎可以确定是空文件/损坏/权限问题
            if (info?.ok && typeof info.size === 'number' && info.size < 1024) {
                tip('录音太短或文件为空，请按住说话 1 秒以上再试')
                lastVoiceFilePath.value = ''
                voiceConfirmVisible.value = false
                return
            }

            // 允许 aac/m4a/mp3 等；若无后缀先放行，交给后端识别
            lastVoiceFilePath.value = filePath
            voiceConfirmVisible.value = true
        })
        .catch((err) => {
            voiceRecording.value = false
            showError(err, '录音失败')
        })
}

async function onHoldEnd() {
    if (!voiceRecording.value) return
    voiceRecording.value = false
    // 关键：松开就停止录
    try { stopHoldRecord() } catch (e) { /* ignore */ }
}

function onHoldCancel() {
    // 触摸被系统打断/取消：也停止录音并丢弃
    voiceRecording.value = false
    lastVoiceFilePath.value = ''
    try { stopHoldRecord() } catch (e) { /* ignore */ }
}

function onVoiceCancelSend() {
    voiceConfirmVisible.value = false
    lastVoiceFilePath.value = ''
    tip('已取消', { type: 'default' })
}

function onVoiceSend() {
    if (!lastVoiceFilePath.value) {
        voiceConfirmVisible.value = false
        return tip('没有可发送的语音')
    }
    return withLoading('voice', async () => {
        try {
            // 2) 上传录音文件到后端
            const uploaded = await apiUploadVoice(lastVoiceFilePath.value)
            const up = normalizeUploadedToAttachment(uploaded, { name: '语音', mime: 'audio/aac' })
            if (!up.url) return tip('录音上传失败：未返回 url')

            // 3) 后端调用 qwen 语音理解，返回可直接用于对话的文本
            const res = await apiVoiceChat({ voiceUrl: up.url, meta: { source: 'voice' } })
            const data = res?.data || res
            const text = data?.text || data?.answer || ''

            voiceConfirmVisible.value = false
            lastVoiceFilePath.value = ''

            if (!text) {
                return tip('语音已上传，但未返回可用文本')
            }

            // 不回填输入框、不提示“已转写”：直接把识别结果作为一条消息发送
            // 说明：onSend 内部会读取 input，因此这里先赋值，再立即触发发送。
            input.value = text
            await new Promise((r) => setTimeout(r, 0))
            await onSend()
        } catch (err) {
            showError(err, '语音识别失败')
        }
    })
}

function buildSendFingerprint(text, attachments) {
    const normalizedText = String(text || '').trim()
    const normalizedAttachments = (attachments || []).map((a) => ({
        type: String(a?.type || ''),
        url: String(a?.url || ''),
        name: String(a?.name || ''),
    }))
    return JSON.stringify({ text: normalizedText, attachments: normalizedAttachments })
}

// 发送消息
function onSend() {
    if (loading.value.send) return

    // 未登录跳转
    if (!getToken()) {
        tip('请先登录')
        uni.navigateTo({ url: '/pages/login/index' })
        return
    }

    const text = input.value.trim()
    const hasText = text.length > 0
    const hasAtt = pendingAttachments.value.length > 0
    if (!hasText && !hasAtt) return tip('请输入问题或先添加图片/文件')

    // 图片理解约束：图片附件必须来自 /files/
    const badImage = pendingAttachments.value.find(a => a.type === 'image' && !isBackendFilesUrl(a.url))
    if (badImage) return tip('检测到非 /files/ 的图片 URL，请重新上传图片后再发送')

    const fp = buildSendFingerprint(text, pendingAttachments.value)
    const now = Date.now()
    if (fp === lastSendFingerprint.value && now - lastSendAt.value < 1500) {
        return
    }
    lastSendFingerprint.value = fp
    lastSendAt.value = now

    return withLoading('send', async () => {
        // 发送后立即清空输入框（让用户感知已提交）
        input.value = ''

        const attachments = pendingAttachments.value.map(a => ({
            type: a.type,
            url: a.url,
            name: a.name,
            size: a.size,
            mime: a.mime,
        }))

        // 若还没有会话 id，先创建一个（标题用用户 첫条消息兜底）
        const createdCid = await ensureConversationId({ title: hasText ? text.slice(0, 24) : '新对话' })

        const payload = {
            ...(createdCid ? { conversationId: createdCid } : {}),
            // 文档约定：允许只发附件不发文字（text 传空字符串）
            text: hasText ? text : '',
            attachments,
            meta: { source: 'composer' },
        }
        console.log('[chat] send payload', payload)

        // 先缓存当前附件，确保失败时可回滚
        const snapshotAtt = [...pendingAttachments.value]

        try {
            const userSummary = [payload.text, ...attachments.map(a => a.type === 'image' ? '[图片]' : `[文件:${a.name || '未命名'}]`)]
                .filter(Boolean)
                .join(' ')

            messages.value.push({ id: `u-${Date.now()}`, role: 'user', text: userSummary })
            showCard.value = false

            // 先清空（成功路径保持清空；失败将回滚）
            pendingAttachments.value = []

            const typingId = `t-${Date.now()}`
            messages.value.push({ id: typingId, role: 'assistant', text: '正在回复中…', pending: true })

            // 先把用户消息落库（用于历史列表 lastMessage/updatedAt 及时变化）
            if (ENABLE_MANUAL_CONVERSATION_APPEND) {
                try {
                    if (createdCid) {
                        await apiAppendConversationMessage(createdCid, {
                            role: 'user',
                            text: userSummary,
                            attachments,
                            clientMsgId: `u-${Date.now()}`,
                        })
                    }
                } catch (e) {
                    console.log('[conversation] append user message failed (ignored)', e)
                }
            }

            const data = await apiSendChat(payload)
            console.log('[chat] send response', data)

            const cid = data?.conversationId || data?.data?.conversationId
            if (cid) currentConversationId.value = cid

            const reply = data?.answer || data?.text || (data?.data && (data.data.answer || data.data.text)) || ''
            const idx = messages.value.findIndex(m => m.id === typingId)
            if (idx !== -1) {
                if (reply) messages.value[idx] = { ...messages.value[idx], text: reply, pending: false }
                else messages.value.splice(idx, 1)
            } else if (reply) {
                messages.value.push({ id: `b-${Date.now()}`, role: 'assistant', text: reply })
            }

            // 把 assistant 回复也落库
            if (ENABLE_MANUAL_CONVERSATION_APPEND) {
                try {
                    const cid2 = currentConversationId.value
                    if (reply && cid2) {
                        await apiAppendConversationMessage(cid2, {
                            role: 'assistant',
                            text: reply,
                            clientMsgId: `a-${Date.now()}`,
                        })
                    }
                } catch (e) {
                    console.log('[conversation] append assistant message failed (ignored)', e)
                }
            }

            await nextTick()
            tip(reply ? '已收到回复' : '已发送（无返回内容）')
        } catch (err) {
            console.error('[chat] send error', err)
            // 失败允许立即重试同一内容
            lastSendFingerprint.value = ''
            lastSendAt.value = 0

            // 出错时移除“正在回复中…”占位（如果存在）
            const idx = messages.value.findIndex(m => m.pending)
            if (idx !== -1) messages.value.splice(idx, 1)

            // 失败回滚附件（按文档：失败不丢附件，方便重试）
            if (!pendingAttachments.value.length && snapshotAtt.length) {
                pendingAttachments.value = snapshotAtt
            }

            showError(err, '发送失败')
            const msg = err?.message || err?.data?.detail || err?.data?.message || ''
            if (err?.statusCode === 401 || /401|unauth|token\b/i.test(String(msg))) {
                currentConversationId.value = null
                uni.navigateTo({ url: '/pages/login/index' })
            }
            return
        }
    })
}

function resetConversation() {
    currentConversationId.value = null
    messages.value = []
    showCard.value = true
    input.value = ''
    pendingAttachments.value = []
    tip('已新建对话', { type: 'success' })
}

// 待发送附件（上传成功后在这里缓存，发送时带到 /api/chat）
const pendingAttachments = ref([])

function removeAttachment(id) {
    pendingAttachments.value = pendingAttachments.value.filter(a => a.id !== id)
}

function normalizeUploadedToAttachment(resData, fallback) {
    // 文档约定：后端保证 data.url
    const data = resData?.data ? resData.data : resData
    const url = data?.url
    const name = data?.name || data?.filename || fallback?.name
    const size = data?.size || fallback?.size
    const mime = data?.mime || data?.contentType || fallback?.mime
    return { url, name, size, mime }
}

function isBackendFilesUrl(url) {
    // 仅允许后端本服务上传返回的 /files/ 路径，避免第三方外链导致后端 400
    // 允许：/files/xxx.png（相对） 或 https://<host>/files/xxx.png（绝对）
    if (!url) return false
    try {
        // 绝对 URL
        if (/^https?:\/\//i.test(url)) {
            const u = new URL(url)
            return u.pathname.startsWith('/files/')
        }
    } catch (e) {
        // ignore
    }
    // 相对 URL
    return url.startsWith('/files/')
}
</script>

<style scoped>
.page {
	height: 100vh;
	background:
		radial-gradient(900rpx 520rpx at 15% 8%, rgba(102, 217, 232, 0.28), transparent 60%),
		radial-gradient(860rpx 520rpx at 85% 16%, rgba(78, 205, 196, 0.22), transparent 58%),
		linear-gradient(180deg, rgba(102, 217, 232, 0.18) 0%, rgba(78, 205, 196, 0.10) 55%, rgba(255, 255, 255, 1) 100%);
	overflow: hidden;
}

.top {
	position: sticky;
	top: 0;
	z-index: 10;
	background: rgba(255, 255, 255, 0.65);
	backdrop-filter: blur(12px);
	-webkit-backdrop-filter: blur(12px);
	border-bottom: 1px solid rgba(27, 31, 42, 0.06);
}

.top-inner {
	height: 52px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 14px;
	position: relative;
}

.top-left,
.top-right {
	width: 44px;
	height: 44px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 14px;
}

.top-left:active,
.top-right:active {
	opacity: 0.7;
}

.top-title {
	position: absolute;
	left: 50%;
	transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 18px;
    font-weight: 800;
    color: #1b1f2a;
    letter-spacing: 0.2px;
}

.top-title-text {
    max-width: 210px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.top-avatar {
    width: 26px;
    height: 26px;
    border-radius: 999px;
    overflow: hidden;
    border: 2px solid rgba(78, 205, 196, 0.35);
    box-shadow: 0 10px 20px rgba(20, 27, 61, 0.12);
}

.top-avatar-img {
    width: 100%;
    height: 100%;
}

.top-left {
	flex: 0 0 44px;
}

.top-actions {
	flex: 0 0 auto;
}

.avatar {
	width: 32px;
	height: 32px;
	border-radius: 999px;
	border: 2px solid rgba(78, 205, 196, 0.35);
	box-shadow: 0 10px 20px rgba(20, 27, 61, 0.12);
	}

.top-actions {
	display: flex;
	align-items: center;
	gap: 10px;
}

.top-action {
	width: 34px;
	height: 34px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: rgba(255, 255, 255, 0.72);
	border-radius: 999px;
	border: 1px solid rgba(27, 31, 42, 0.06);
	box-shadow: 0 10px 22px rgba(20, 27, 61, 0.10);
}

.top-action:active {
	transform: scale(0.98);
}

.orb {
	width: 20px;
	height: 20px;
	border-radius: 999px;
	background:
		radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.0) 55%),
		radial-gradient(circle at 60% 60%, rgba(102, 217, 232, 0.85), rgba(78, 205, 196, 0.70) 60%, rgba(78, 205, 196, 0.25) 100%);
	box-shadow:
		0 10px 20px rgba(78, 205, 196, 0.26),
		0 2px 8px rgba(102, 217, 232, 0.18);
}


.body {
    height: calc(100vh - 52px);
    /* padding-bottom 交由 bodyStyle 动态控制，避免多行输入时遮挡最后消息 */
    padding: 14px 14px 180px;
}

.hero {
	padding: 18px 6px 10px;
	text-align: center;
}

.hero-logo {
	width: 86px;
	height: 86px;
	margin: 6px auto 10px;
	position: relative;
}

.logo-ring {
	position: absolute;
	inset: 0;
	border-radius: 999px;
	background: conic-gradient(from 210deg, #4ecdc4, #66d9e8, #88e6ff, #4ecdc4);
	filter: drop-shadow(0 14px 24px rgba(78, 205, 196, 0.22));
	animation: spin 5.8s linear infinite;
}

.logo-core {
	position: absolute;
	inset: 10px;
    overflow: hidden;
	border-radius: 999px;

.logo-avatar {
    width: 100%;
    height: 100%;
    border-radius: 999px;
    display: block;
    /* 轻微描边，避免浅色头像融进背景 */
    box-shadow: inset 0 0 0 1px rgba(27, 31, 42, 0.06);
}
	background: rgba(255, 255, 255, 0.85);
	box-shadow: 0 14px 28px rgba(20, 27, 61, 0.12);
}

@keyframes spin {
	to {
		transform: rotate(360deg);
	}
}

.hero-title {
	font-size: 22px;
	font-weight: 800;
	color: #1b1f2a;
	line-height: 1.25;
	margin-top: 8px;
}

.hero-strong {
	color: #1b1f2a;
}

.hero-sub {
	margin-top: 8px;
	color: rgba(27, 31, 42, 0.45);
	font-size: 13px;
}

.chat-area {
    margin: 10px auto;
    width: calc(100% - 10%);
    max-width: 920px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.chat-msg {
    display: flex;
    align-items: flex-end;
}

.chat-msg.user {
    justify-content: flex-end;
}

.chat-msg.assistant {
    justify-content: flex-start;
}

.bubble {
    display: inline-block;
    padding: 10px 14px;
    border-radius: 16px;
    max-width: 76%;
    line-height: 1.45;
}

/* 助手气泡：白底、深色文字、轻阴影 */
.chat-msg.assistant .bubble {
    background: rgba(255,255,255,0.96);
    color: #1b1f2a;
    box-shadow: 0 8px 20px rgba(20,27,61,0.06);
    border: 1px solid rgba(27,31,42,0.04);
    border-top-left-radius: 6px;
    border-top-right-radius: 16px;
    border-bottom-right-radius: 16px;
    border-bottom-left-radius: 16px;
    position: relative;
}

/* 用户气泡：主题渐变、白字、强阴影，靠右显示 */
.chat-msg.user .bubble {
    background: linear-gradient(180deg, rgba(78, 205, 197, 0.747) 0%, rgba(102, 217, 232, 0.856) 100%);
    color: #ffffff;
    box-shadow: 0 12px 28px rgba(78,205,196,0.18);
    border-top-left-radius: 16px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    border-bottom-left-radius: 16px;
    margin-right: 5%;
    position: relative;
}

/* 小尾巴：assistant 在左，user 在右 */
.chat-msg.assistant .bubble::after,
.chat-msg.user .bubble::after {
    content: '';
    position: absolute;
    width: 12px;
    height: 12px;
    bottom: 8px;
    transform: rotate(45deg);
}
.chat-msg.assistant .bubble::after {
    left: -6px;
    background: rgba(255,255,255,0.96);
    border-left: 1px solid rgba(27,31,42,0.04);
    border-bottom: 1px solid rgba(27,31,42,0.04);
}
.chat-msg.user .bubble::after {
    right: -6px;
    background: linear-gradient(180deg, rgba(78,205,196,1) 0%, rgba(102,217,232,1) 100%);
}

.card-wrap {
    margin-top: 12px;
    /* 卡片宽度：左侧保留 5%，右侧保留 7%（总 12%） */
    width: calc(100% - 15%);
    max-width: 920px; /* 可按需调整最大宽度 */
    padding: 0;
    margin-left: 5%;
    margin-right: 10%;
    position: relative;
}

.card {
    border-radius: clamp(16px, 4vw, 36px);
    overflow: hidden;
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid rgba(177, 181, 192, 0.39);
    box-shadow:
        0 18px 34px rgba(116, 117, 123, 0.358),
        0 2px 0 rgba(255, 255, 255, 0.6) inset;
}

.card-hd {
    display: flex;
    align-items: center;
    justify-content: space-between;
    /* 响应式内边距，保证左右各有合理留白 */
    padding: clamp(10px, 1.6vw, 14px) clamp(16px, 4vw, 24px) clamp(8px, 1.2vw, 10px);
}

.card-title {
    /* 响应式标题：在窄屏时略微缩小 */
    font-size: clamp(14px, 2.5vw, 16px);
    font-weight: 800;
    color: #1b1f2a;
}

.card-action {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 8px 10px;
	border-radius: 999px;
	background: rgba(78, 205, 196, 0.12);
}

.card-action:active {
	opacity: 0.75;
}

.card-action-text {
	font-size: 12px;
	color: #2baaa2;
	font-weight: 700;
}

.q-list {
    padding: 0 clamp(12px, 3.2vw, 18px) clamp(12px, 2.8vw, 14px);
    display: flex;
    flex-direction: column;
    gap: clamp(10px, 2.6vw, 12px);
}

.card-ft {
    padding: 4px clamp(12px, 3.6vw, 18px) 18px;
    display: flex;
    justify-content: center;
}

.shuffle-text {
    margin-left: 6px;
    font-size: clamp(12px, 2.2vw, 13px);
    color: #ffffff;
    font-weight: 800;
}

.q-item {
    position: relative;
    background: rgba(245, 251, 251, 1);
    border: 1px solid rgba(78, 205, 196, 0.18);
    border-radius: clamp(12px, 3vw, 20px);
    padding: clamp(10px, 2.8vw, 14px) clamp(12px, 3vw, 16px);
    display: flex;
    gap: clamp(8px, 2.4vw, 10px);
    align-items: flex-start;
    box-shadow: 0 10px 18px rgba(20, 27, 61, 0.06);
}

@media (max-width: 360px) {
	.card-wrap {
		padding: 0 6px;
	}
	.q-list {
		padding-left: 12px;
		padding-right: 12px;
	}
}

.q-item:active {
	transform: scale(0.99);
	opacity: 0.9;
}

.q-quote {
    width: clamp(20px, 4vw, 26px);
    height: clamp(20px, 4vw, 26px);
    border-radius: 50%;
    background: rgba(78, 205, 196, 0.16);
    color: #2baaa2;
    font-size: clamp(14px, 2.8vw, 18px);
    font-weight: 900;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
}

.q-text {
    flex: 1;
    font-size: clamp(13px, 2.4vw, 15px);
    line-height: 1.35;
    color: #1b1f2a;
}

.q-go {
	margin-top: 2px;
	flex: 0 0 auto;
	opacity: 0.75;
}

.spacer {
    /* 作为滚动结尾的额外占位，配合 .body 的 padding-bottom 使用，保证可视区域留白 */
    height: 160px;
}

.composer {
	position: fixed;
	left: 0;
	right: 0;
	bottom: 0;
	padding: 10px 12px;
	background: rgba(255, 255, 255, 0.82);
	backdrop-filter: blur(14px);
	-webkit-backdrop-filter: blur(14px);
	border-top: 1px solid rgba(27, 31, 42, 0.06);
}

.composer-inner {
    width: min(720px, 100%);
    margin: 0 auto;
    display: flex;
    align-items: flex-end;
    /* 缩小按钮间距，给输入框更多宽度 */
    gap: 6px;
}

.input-wrap {
	flex: 1;
	background: rgba(255, 255, 255, 0.92);
	border: 1px solid rgba(27, 31, 42, 0.08);
	border-radius: 999px;
	box-shadow: 0 10px 22px rgba(20, 27, 61, 0.10);
	overflow: hidden;
	padding: 2px 0;
	min-height: 44px;
}

/* 微信式语音输入：按住说话 */
.hold-to-talk {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 44px;
    padding: 4px 10px;
}

.hold-btn {
    flex: 1;
    text-align: center;
    font-size: 16px;
    font-weight: 700;
    color: rgba(27, 31, 42, 0.80);
    background: rgba(245, 251, 251, 1);
    border: 1px solid rgba(78, 205, 196, 0.22);
    border-radius: 999px;
    padding: 10px 12px;
    user-select: none;
}

.hold-to-talk.is-recording .hold-btn {
    background: rgba(78, 205, 196, 0.14);
    border-color: rgba(78, 205, 196, 0.48);
    color: rgba(27, 31, 42, 0.92);
}

.voice-confirm {
    width: min(320px, 84vw);
    background: rgba(255, 255, 255, 0.96);
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 16px 40px rgba(20, 27, 61, 0.22);
}

.voice-confirm-title {
    font-size: 16px;
    font-weight: 800;
    color: #1b1f2a;
}

.voice-confirm-sub {
    margin-top: 6px;
    font-size: 13px;
    color: rgba(27, 31, 42, 0.55);
}

.voice-confirm-actions {
    margin-top: 14px;
    display: flex;
    gap: 10px;
    justify-content: flex-end;
}

/* textarea 模式下 u-input 内部会自增高度：允许自然换行，不做截断 */
.input-wrap :deep(textarea) {
	max-height: 220px;
	overflow-y: auto;
	overflow-x: hidden;
	white-space: pre-wrap;
	word-break: break-word;
	word-wrap: break-word;
	line-break: anywhere;
	padding-right: 8px;
}

/* 避免 uView 内部 wrapper 产生单行截断 */
.input-wrap :deep(.u-input__content),
.input-wrap :deep(.u-input__inner) {
	white-space: pre-wrap;
}

/* “正在回复中”占位的轻量动效 */
.chat-msg.assistant .bubble.pending {
    color: rgba(27,31,42,.55);
}

.chat-msg.assistant .bubble.pending::before {
    content: '';
    display: inline-block;
    width: 10px;
    height: 10px;
    margin-right: 8px;
    border-radius: 999px;
    border: 2px solid rgba(78,205,196,.25);
    border-top-color: rgba(78,205,196,.9);
    animation: spinMini 0.9s linear infinite;
    vertical-align: -1px;
}

@keyframes spinMini {
    to { transform: rotate(360deg); }
}

.attach-strip {
    width: min(720px, 100%);
    margin: 6px auto 0;
    padding: 0 2px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.attach-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,.86);
    border: 1px solid rgba(27,31,42,.06);
    box-shadow: 0 10px 22px rgba(20, 27, 61, 0.08);
    max-width: 100%;
}

.attach-thumb {
    width: 14px;
    height: 14px;
    border-radius: 4px;
    border: 1px solid rgba(78, 205, 196, 0.35);
    box-shadow: 0 6px 14px rgba(78, 205, 196, 0.14);
    flex: 0 0 auto;
}

.attach-chip-text {
    font-size: 12px;
    color: rgba(27,31,42,.8);
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.attach-chip-x {
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: rgba(27,31,42,.04);
}

.attach-hint {
    width: 100%;
    margin-top: 6px;
    font-size: 12px;
    color: rgba(27,31,42,.55);
    padding-left: 2px;
}
</style>
