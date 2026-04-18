<template>
	<view class="page">
		<view class="hd">
			<view class="title">账号管理</view>
			<view class="sub">管理登录状态与退出登录</view>
		</view>

		<view class="card">
			<view class="row between">
				<view class="left">
					<view class="badge" :class="loggedIn ? 'on' : 'off'">{{ loggedIn ? '已登录' : '未登录' }}</view>
					<view class="who">
						<view class="name">{{ activeAccount?.name || '访客' }}</view>
						<view class="meta">{{ activeAccount?.desc || '请先登录后使用完整功能' }}</view>
					</view>
				</view>
			</view>
		</view>

		<view class="section">
			<view class="section-title">账号信息</view>
			<view class="list">
				<view
					v-for="acc in accounts"
					:key="acc.id"
					class="item"
				>
					<view class="item-left">
						<view class="avatar" aria-hidden="true">{{ acc.name.slice(0, 1) }}</view>
						<view class="info">
							<view class="item-name">{{ acc.name }}</view>
							<view class="item-sub">账号：{{ acc.account }}</view>
						</view>
					</view>
					<view class="item-right">
						<view class="tag">当前</view>
					</view>
				</view>
			</view>
		</view>

		<view class="section">
			<view class="section-title">安全</view>
			<view class="actions">
				<u-button
					v-if="loggedIn"
					type="error"
					shape="circle"
					:customStyle="logoutBtn"
					@tap="logout"
				>
					退出登录
				</u-button>
				<u-button
					v-else
					type="primary"
					shape="circle"
					:customStyle="smallBtn"
					@tap="goLogin"
				>
					去登录
				</u-button>
				<u-button type="default" shape="circle" :customStyle="ghostBtn" @tap="goBack">返回</u-button>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { apiDeleteAccount, apiListAccounts, apiMe, apiSwitchAccount } from '@/services/api'
import { clearToken, getToken } from '@/services/storage'

// 真实账号列表（来自后端）
const accounts = ref([])
const activeId = ref('')
const loggedIn = ref(!!getToken())
const me = ref(null)

const activeAccount = computed(() => {
	return accounts.value.find((x) => x.id === activeId.value) || me.value || null
})

const smallBtn = {
	background: 'linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%)',
	border: 'none',
	padding: '0 14px',
	height: '34px',
	boxShadow: '0 14px 26px rgba(78, 205, 196, .22)',
	fontWeight: '800',
}

const logoutBtn = {
	width: '100%',
	height: '44px',
	borderRadius: '999px',
	fontWeight: '800',
}

const ghostBtn = {
	width: '100%',
	height: '44px',
	borderRadius: '999px',
	background: 'rgba(255,255,255,.85)',
	border: '1px solid rgba(27,31,42,.10)',
	fontWeight: '800',
}

function normalizeAccount(item) {
	return {
		id: String(item?.id || item?.accountId || item?.account || ''),
		name: item?.name || item?.nickname || item?.displayName || item?.account || '未命名',
		account: item?.account || item?.username || item?.login || '',
	}
}

async function refresh() {
	loggedIn.value = !!getToken()
	if (!loggedIn.value) {
		me.value = null
		accounts.value = []
		activeId.value = ''
		return
	}
	try {
		const meRes = await apiMe()
		me.value = normalizeAccount(meRes?.data || {})
	} catch (e) {
		// me 接口可选：没有也不阻塞列表
		me.value = null
	}
	try {
		const listRes = await apiListAccounts()
		const list = Array.isArray(listRes?.data?.items) ? listRes.data.items : Array.isArray(listRes?.data) ? listRes.data : []
		accounts.value = list.map(normalizeAccount).filter((x) => x.id).slice(0, 1)
		if (!activeId.value) {
			activeId.value = accounts.value[0]?.id || me.value?.id || ''
		}
	} catch (err) {
		uni.showToast({ title: err?.message || err?.data?.detail || '获取账号列表失败', icon: 'none' })
	}
}

onMounted(() => {
	refresh()
})

// 从登录页返回时刷新（uni-app 生命周期）
onShow(() => {
	refresh()
})

async function switchAccount(id) {
	if (!loggedIn.value) {
		uni.showToast({ title: '请先登录', icon: 'none' })
		return uni.navigateTo({ url: '/pages/login/index' })
	}
	activeId.value = id
	try {
		// 后端若不需要 activeAccount 概念，可实现为空操作（200 ok）
		await apiSwitchAccount(id)
		uni.showToast({ title: '已切换账号', icon: 'none' })
	} catch (err) {
		const status = Number(err?.status || err?.statusCode)
		if (status === 409) {
			uni.showToast({ title: '当前为单账号模式，不支持该操作', icon: 'none' })
			return
		}
		uni.showToast({ title: err?.message || err?.data?.detail || '切换失败', icon: 'none' })
	}
}

function onAddAccount() {
	// 新增账号通过“登录另一个账号”实现
	// 登录成功后会保存 token；返回本页时会 refresh() 拉取账号列表
	uni.navigateTo({ url: '/pages/login/index' })
}

function onDeleteAccount(id) {
	if (!loggedIn.value) return
	if (accounts.value.length <= 1) {
		return uni.showToast({ title: '至少保留 1 个账号', icon: 'none' })
	}
	const acc = accounts.value.find((x) => x.id === id)
	uni.showModal({
		title: '删除账号',
		content: `确定删除“${acc?.name || '该账号'}”吗？`,
		confirmText: '删除',
		confirmColor: '#ff6b6b',
		success: async (res) => {
			if (!res.confirm) return
			try {
				await apiDeleteAccount(id)
				accounts.value = accounts.value.filter((x) => x.id !== id)
				if (activeId.value === id) {
					activeId.value = accounts.value[0]?.id || ''
				}
				uni.showToast({ title: '已删除', icon: 'none' })
			} catch (err) {
					const status = Number(err?.status || err?.statusCode)
					if (status === 409) {
						uni.showToast({ title: '当前为单账号模式，不支持该操作', icon: 'none' })
						return
					}
					uni.showToast({ title: err?.message || err?.data?.detail || '删除失败', icon: 'none' })
			}
		},
	})
}

function logout() {
	uni.showModal({
		title: '退出登录',
		content: '确定要退出当前账号吗？',
		success: (res) => {
			if (!res.confirm) return
			loggedIn.value = false
			clearToken()
			accounts.value = []
			activeId.value = ''
			me.value = null
			uni.showToast({ title: '已退出登录', icon: 'none' })
		},
	})
}

function goLogin() {
	uni.navigateTo({ url: '/pages/login/index' })
}

function goBack() {
	uni.navigateBack()
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

.hd {
	text-align: center;
	padding: 10px 6px 14px;
}

.title {
	font-size: 20px;
	font-weight: 900;
	color: #1b1f2a;
}

.sub {
	margin-top: 8px;
	font-size: 13px;
	color: rgba(27, 31, 42, 0.55);
}

.card {
	background: rgba(255, 255, 255, 0.92);
	border: 1px solid rgba(27, 31, 42, 0.08);
	border-radius: 18px;
	padding: 14px;
	box-shadow: 0 22px 42px rgba(20, 27, 61, 0.12);
}

.row {
	display: flex;
	align-items: center;
	gap: 12px;
}

.between {
	justify-content: space-between;
}

.left {
	display: flex;
	align-items: center;
	gap: 10px;
}

.badge {
	padding: 6px 10px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 800;
	border: 1px solid rgba(27, 31, 42, 0.10);
	background: rgba(255, 255, 255, 0.75);
	color: rgba(27, 31, 42, 0.70);
}

.badge.on {
	border-color: rgba(78, 205, 196, 0.22);
	background: rgba(78, 205, 196, 0.12);
	color: rgba(22, 122, 118, 0.95);
}

.badge.off {
	border-color: rgba(255, 107, 107, 0.22);
	background: rgba(255, 107, 107, 0.12);
	color: rgba(176, 53, 53, 0.95);
}

.who {
	display: flex;
	flex-direction: column;
	gap: 3px;
}

.name {
	font-size: 15px;
	font-weight: 900;
	color: #1b1f2a;
}

.meta {
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.section {
	margin-top: 14px;
}

.section-title {
	font-size: 13px;
	font-weight: 900;
	color: rgba(27, 31, 42, 0.65);
	margin: 0 6px 10px;
}

.list {
	background: rgba(255, 255, 255, 0.92);
	border: 1px solid rgba(27, 31, 42, 0.08);
	border-radius: 18px;
	overflow: hidden;
}

.item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 12px 12px;
}

.item-left {
	display: flex;
	align-items: center;
	gap: 10px;
}

.avatar {
	width: 34px;
	height: 34px;
	border-radius: 999px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #ffffff;
	font-weight: 900;
	background: linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%);
	box-shadow: 0 14px 26px rgba(78, 205, 196, 0.22);
}

.info {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.item-name {
	font-size: 14px;
	font-weight: 900;
	color: #1b1f2a;
}

.item-sub {
	font-size: 12px;
	color: rgba(27, 31, 42, 0.50);
}

.item-right {
	display: flex;
	align-items: center;
}

.tag {
	padding: 4px 10px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 900;
	background: rgba(78, 205, 196, 0.12);
	border: 1px solid rgba(78, 205, 196, 0.22);
	color: rgba(22, 122, 118, 0.95);
}

.actions {
	display: flex;
	flex-direction: column;
	gap: 10px;
}
</style>
