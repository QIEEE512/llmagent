<template>
	<view class="page">
		<view class="stage">
			<view class="top-bar" aria-hidden="true"></view>

			<!-- 右侧装饰（简化版，避免跨端 svg 兼容问题） -->
			<view class="art">
				<view class="art-orb"></view>
				<view class="art-pill"></view>
			</view>

			<view class="card" aria-label="账号密码登录">
				<view class="brand">
					<view class="logo">Q</view>
					<view class="name">预留位置</view>
				</view>

				<view class="h1">{{ mode === 'login' ? 'Hello, 欢迎登录' : 'Hello, 欢迎注册' }}</view>
				<view class="subtitle">WELCOME TO THE SYSTEM</view>

				<!-- 登录 -->
				<view v-if="mode === 'login'" class="form">
					<view class="field">
						<u-icon name="account" size="20" :color="iconColor" />
						<input
							v-model="login.account"
							class="ipt"
							placeholder="请输入账号"
							confirm-type="done"
							@input="clearLoginError"
						/>
					</view>

					<view class="field password">
						<u-icon name="lock" size="20" :color="iconColor" />
						<input
							v-model="login.password"
							class="ipt"
							:password="!login.showPwd"
							placeholder="请输入密码"
							confirm-type="done"
							@input="clearLoginError"
						/>
						<view class="toggle" @tap="login.showPwd = !login.showPwd">
							<u-icon :name="login.showPwd ? 'eye-fill' : 'eye-off'" size="20" color="rgba(27,31,42,.45)" />
						</view>
					</view>

					<view class="row">
						<view class="check" @tap="remember = !remember">
							<view class="box" :class="{ on: remember }"></view>
							<text>记住账号</text>
						</view>
						<text class="link" @tap="tip('原型演示：请联系管理员重置密码')">忘记密码？</text>
					</view>

					<view class="btn-wrap">
						<u-button
							type="primary"
							shape="circle"
							:customStyle="btnStyle"
							:loading="loading"
							:disabled="!canLogin"
							@tap="onLogin"
						>
							登 录
						</u-button>
					</view>

					<!-- 登录错误提示 -->
					<view v-if="loginError" class="error-text">{{ loginError }}</view>

					<view class="row2">
						<text>还没有账号？</text>
						<text class="pill" @tap="mode = 'register'">注册账号</text>
					</view>
				</view>

				<!-- 注册 -->
				<view v-else class="form">
					<view class="field">
						<u-icon name="account" size="20" :color="iconColor" />
						<input v-model="reg.name" class="ipt" placeholder="请输入昵称" />
					</view>

					<view class="field">
						<u-icon name="edit-pen" size="20" :color="iconColor" />
						<input v-model="reg.account" class="ipt" placeholder="请输入账号（邮箱/用户名）" />
					</view>

					<view class="field">
						<u-icon name="phone" size="20" :color="iconColor" />
						<input v-model="reg.phone" class="ipt" placeholder="手机号（可选）" />
					</view>

					<view class="field password">
						<u-icon name="lock" size="20" :color="iconColor" />
						<input v-model="reg.password" class="ipt" :password="!reg.showPwd" placeholder="设置密码（至少 6 位）" />
						<view class="toggle" @tap="reg.showPwd = !reg.showPwd">
							<u-icon :name="reg.showPwd ? 'eye-fill' : 'eye-off'" size="20" color="rgba(27,31,42,.45)" />
						</view>
					</view>

					<view class="field">
						<u-icon name="checkmark" size="20" :color="iconColor" />
						<input v-model="reg.password2" class="ipt" :password="true" placeholder="再次输入密码" />
					</view>

					<view class="btn-wrap">
						<u-button
							type="primary"
							shape="circle"
							:customStyle="btnStyle"
							:loading="loading"
							:disabled="!canRegister"
							@tap="onRegister"
						>
							注 册
						</u-button>
					</view>

					<view class="row2">
						<text>已有账号？</text>
						<text class="pill" @tap="mode = 'login'">返回登录</text>
					</view>

					<view class="hint">
						注册接口预留：POST /api/auth/register（示例）。
						<text class="muted">实际对接时请替换为你的后端账户数据库服务。</text>
					</view>
				</view>
			</view>
		</view>

		<u-toast ref="toastRef" />
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'

import { apiLogin as netLogin, apiRegister as netRegister } from '@/services/api'
import { setToken } from '@/services/storage'

const toastRef = ref(null)
const mode = ref('login') // login | register
const remember = ref(true)
const loading = ref(false)

// 处理底部安全区，避免出现“灰色矩形”占位（特别是某些 WebView/安卓机型）
const safeBottom = ref(0)
try {
	safeBottom.value = uni.getSystemInfoSync?.().safeAreaInsets?.bottom || 0
} catch (e) {
	safeBottom.value = 0
}

const iconColor = 'rgba(78,205,196,.92)'

// 调试默认账号：1008611/1008611（仅用于联调；其他账号需先走注册）
const login = ref({ account: '1008611', password: '1008611', showPwd: false })
// 登录错误文本（用于页面下方的显式错误提示）
const loginError = ref('')
const reg = ref({ name: '', account: '', phone: '', password: '', password2: '', showPwd: false })

const canLogin = computed(() => login.value.account.trim() && login.value.password.trim().length >= 6)
const canRegister = computed(() => {
	return (
		reg.value.name.trim() &&
		reg.value.account.trim() &&
		reg.value.password.length >= 6 &&
		reg.value.password2.length >= 6 &&
		reg.value.password === reg.value.password2
	)
})

const btnStyle = {
	background: 'linear-gradient(180deg, rgba(102, 217, 232, 1) 0%, rgba(78, 205, 196, 1) 55%, rgba(53, 186, 178, 1) 100%)',
	border: 'none',
	width: '100%',
	height: '44px',
	boxShadow: '0 18px 30px rgba(78, 205, 196, .30)',
	fontWeight: '800',
}

function tip(msg) {
	// 如果 u-view 的 <u-toast> 可用则使用其 show 方法
	try {
		if (toastRef.value && typeof toastRef.value.show === 'function') {
			toastRef.value.show({ message: msg })
			console.log('[tip] via u-toast:', msg)
			return
		}
	} catch (e) {
		console.warn('[tip] u-toast show failed', e)
	}

	// 回退到 uni.showToast（大多数 uni-app 平台支持）
	try {
		uni.showToast({ title: String(msg || ''), icon: 'none', duration: 2500 })
		console.log('[tip] via uni.showToast:', msg)
		return
	} catch (e) {
		console.warn('[tip] uni.showToast failed', e)
	}

	// 最后兜底：H5/任何环境下使用 alert，确保用户能看到（仅在无法显示 toast 时触发）
	try {
		if (typeof window !== 'undefined' && typeof window.alert === 'function') {
			// 小延迟以避免阻塞当前执行栈
			setTimeout(() => window.alert(String(msg || '')), 50)
			console.log('[tip] via window.alert:', msg)
			return
		}
	} catch (e) {
		console.warn('[tip] window.alert failed', e)
	}

	// 最后回退到控制台输出
	console.log('[tip] fallback:', msg)
}

function clearLoginError() {
	loginError.value = ''
}

function showError(err, fallback) {
	const msg = err?.message || err?.data?.detail || err?.data?.message || fallback || '请求失败'
	tip(msg)
}

async function onLogin() {
	if (!canLogin.value) return tip('请输入账号与至少 6 位密码')
	// 每次尝试登录前清理上次的页面错误提示
	loginError.value = ''
	loading.value = true
	try {
		const payload = { account: login.value.account.trim(), password: login.value.password }
		console.log('[login] start', payload.account)
		const res = await netLogin(payload)
		// 兼容后端字段差异：accessToken/token/access_token
		const token = res?.data?.accessToken || res?.data?.token || res?.data?.access_token
		console.log('[login] response', res)
		if (!token) {
			tip('登录成功但未返回 token，请检查后端 data.accessToken')
			return
		}
		setToken(token)
		// 登录成功清除错误提示并跳转
		loginError.value = ''
		tip('登录成功，正在跳转…')
		setTimeout(() => {
			uni.reLaunch({ url: '/pages/chat/index' })
		}, 150)
	} catch (err) {
		console.log('[login] error', err)
		// 更友好的认证失败提示：如果后端返回 401/401-like code，或错误信息中包含账号/密码相关关键词
		const msg = err?.message || err?.data?.detail || err?.data?.message || ''
		const status = err?.status || err?.statusCode || err?.data?.status || err?.data?.code
		const isAuthError = Number(status) === 401 || /401|unauth|invalid credential|invalid credentials|账号|密码|认证失败|未授权|凭证/i.test(String(msg))
		if (isAuthError) {
			loginError.value = '账号或密码有误'
			tip('账号或密码有误')
		} else {
			const fallback = msg || '登录失败'
			loginError.value = fallback
			showError(err, '登录失败')
		}
	} finally {
		loading.value = false
	}
}

async function onRegister() {
	if (!canRegister.value) return tip('请完整填写注册信息')
	loading.value = true
	try {
		await netRegister({
			name: reg.value.name.trim(),
			account: reg.value.account.trim(),
			phone: reg.value.phone.trim(),
			password: reg.value.password,
		})
		login.value.account = reg.value.account
		login.value.password = ''
		mode.value = 'login'
		tip('注册成功，请登录')
	} catch (err) {
		showError(err, '注册失败')
	} finally {
		loading.value = false
	}
}
</script>

<style scoped>
.page {
	height: 100vh;
	overflow: hidden;
	background:
		radial-gradient(900rpx 520rpx at 15% 8%, rgba(102, 217, 232, 0.28), transparent 60%),
		radial-gradient(860rpx 520rpx at 85% 16%, rgba(78, 205, 196, 0.22), transparent 58%),
		linear-gradient(160deg, #88e6ff 0%, #66d9e8 45%, #4ecdc4 100%);
}

.stage {
	width: 100%;
	height: 100vh;
	padding: 22px 18px;
	padding-bottom: calc(18px + env(safe-area-inset-bottom));
	display: flex;
	align-items: center;
	justify-content: center;
	position: relative;
	overflow: hidden;
}

.top-bar {
	position: absolute;
	left: 0;
	right: 0;
	top: 0;
	height: 56px;
	background: linear-gradient(180deg, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0));
	backdrop-filter: blur(6px);
	-webkit-backdrop-filter: blur(6px);
	border-bottom: 1px solid rgba(255, 255, 255, 0.10);
	border-bottom-left-radius: 18px;
	border-bottom-right-radius: 18px;
}

.art {
	position: absolute;
	right: -22px;
	top: 116px;
	width: 210px;
	height: 380px;
	pointer-events: none;
	opacity: 0.95;
	filter: drop-shadow(0 22px 40px rgba(0, 0, 0, 0.18));
}

.art-orb {
	position: absolute;
	right: 0;
	top: 40px;
	width: 150px;
	height: 150px;
	border-radius: 999px;
	background: radial-gradient(circle at 35% 30%, rgba(255, 255, 255, 0.62), rgba(255, 255, 255, 0.10) 55%),
		radial-gradient(circle at 60% 60%, rgba(102, 217, 232, 0.92), rgba(78, 205, 196, 0.75) 60%, rgba(78, 205, 196, 0.22) 100%);
}

.art-pill {
	position: absolute;
	right: 14px;
	top: 130px;
	width: 90px;
	height: 200px;
	border-radius: 22px;
	background: rgba(255, 255, 255, 0.14);
	border: 1px solid rgba(255, 255, 255, 0.22);
}

.card {
	margin-top: -120px;
	width: calc(100% - 18%);
	max-width: 360px;
	background: rgba(255, 255, 255, 0.92);
	border: 1px solid rgba(255, 255, 255, 0.55);
	border-radius: 20px;
	box-shadow: 0 18px 45px rgba(20, 27, 61, 0.22);
	padding: 22px 18px 18px;
	position: relative;
	overflow: auto;
	margin-left: 5%;
    margin-right: 13%;
	z-index: 1;
}

.card::before {
	content: '';
	position: absolute;
	inset: -1px;
	background:
		radial-gradient(520px 260px at 16% 6%, rgba(78, 205, 196, 0.16), transparent 55%),
		radial-gradient(420px 220px at 100% 0%, rgba(102, 217, 232, 0.14), transparent 60%);
	pointer-events: none;
}

.brand {
	position: relative;
	display: flex;
	align-items: center;
	gap: 10px;
	margin-bottom: 10px;
}

.logo {
	width: 34px;
	height: 34px;
	border-radius: 12px;
	background: linear-gradient(145deg, rgba(78, 205, 196, 1), rgba(102, 217, 232, 0.92));
	box-shadow: 0 10px 18px rgba(78, 205, 196, 0.24);
	display: flex;
	align-items: center;
	justify-content: center;
	color: #fff;
	font-weight: 900;
}

.name {
	font-weight: 800;
	font-size: 15px;
	color: #2a2f3e;
	letter-spacing: 0.2px;
}

.h1 {
	position: relative;
	margin: 6px 0 4px;
	font-size: 20px;
	font-weight: 900;
	color: #1b1f2a;
}

.subtitle {
	position: relative;
	margin: 0 0 14px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.45);
	letter-spacing: 0.4px;
	text-transform: uppercase;
}

.form {
	position: relative;
	display: flex;
	flex-direction: column;
	gap: 10px;
	margin-top: 10px;
}

.field {
	background: rgba(255, 255, 255, 0.86);
	border: 1px solid rgba(27, 31, 42, 0.06);
	border-radius: 14px;
	padding: 12px 12px;
	display: flex;
	align-items: center;
	gap: 10px;
	box-shadow: 0 10px 22px rgba(20, 27, 61, 0.08), 0 2px 0 rgba(255, 255, 255, 0.75) inset;
}

.field.password {
	background:
		radial-gradient(260px 120px at 20% 10%, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.72)),
		linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(245, 251, 251, 0.86));
	border: 1px solid rgba(78, 205, 196, 0.18);
}

.error-text {
	margin-top: 10px;
	display: inline-block;
	padding: 6px 12px;
	border-radius: 999px;
	background: linear-gradient(180deg, rgba(78,205,196,0.08), rgba(78,205,196,0.04));
	border: 1px solid rgba(78,205,196,0.18);
	color: #0f4f46; /* 深色但更贴合主题 */
	font-size: 13px;
	text-align: center;
	width: auto;
	margin-left: auto;
	margin-right: auto;
}

@media (max-width: 420px) {
	.error-text {
		font-size: 12px;
		padding: 5px 10px;
	}
}

.ipt {
	flex: 1;
	font-size: 14px;
	color: #1b1f2a;
}

.toggle {
	padding: 6px;
	border-radius: 10px;
}

.row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-top: 2px;
	padding: 0 2px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.45);
}

.btn-wrap {
	width: 100%;
	pointer-events: auto;
}

.check {
	display: flex;
	align-items: center;
	gap: 8px;
}

.box {
	width: 16px;
	height: 16px;
	border-radius: 4px;
	border: 1px solid rgba(27, 31, 42, 0.18);
	background: rgba(255, 255, 255, 0.7);
}

.box.on {
	border-color: rgba(78, 205, 196, 0.35);
	background: rgba(78, 205, 196, 0.20);
}

.link {
	color: rgba(22, 122, 118, 0.95);
	font-weight: 800;
}

.row2 {
	margin-top: 10px;
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 10px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.pill {
	padding: 8px 12px;
	border-radius: 999px;
	font-weight: 900;
	color: rgba(22, 122, 118, 0.95);
	background: rgba(255, 255, 255, 0.55);
	border: 1px solid rgba(78, 205, 196, 0.18);
	box-shadow: 0 12px 24px rgba(78, 205, 196, 0.12);
}

.hint {
	margin-top: 10px;
	font-size: 11px;
	color: rgba(27, 31, 42, 0.55);
	line-height: 1.5;
}

.muted {
	display: block;
	color: rgba(27, 31, 42, 0.50);
	margin-top: 4px;
}
</style>
