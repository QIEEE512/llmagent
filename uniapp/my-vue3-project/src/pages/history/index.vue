<template>
	<view class="page">
		<scroll-view class="body" scroll-y>
			<!-- 空态：按截图居中展示 -->
			<view v-if="!conversations.length" class="empty-wrap">
				<view class="empty">暂无历史对话</view>
			</view>

			<!-- 列表态 -->
			<view v-else>
				<view v-for="conversation in conversations" :key="conversation.conversationId" class="conversation-item" @click="goToConversation(conversation)" @longpress="onLongPressConversation(conversation)">
					<view class="title">{{ conversation.title || '未命名对话' }}</view>
					<view class="last-message">{{ conversation.lastMessage || '' }}</view>
					<view class="timestamp">{{ formatDate(conversation.updatedAt) }}</view>
				</view>
			</view>
		</scroll-view>

		<!-- 底部固定操作栏：左 新对话 / 右 我的空间 -->
		<view class="bottom-bar">
			<u-button type="primary" shape="circle" :customStyle="bottomBtnPrimaryStyle" @click="createNewConversation">新对话</u-button>
			<u-button type="default" shape="circle" :customStyle="bottomBtnGhostStyle" @click="goMySpace">我的空间</u-button>
		</view>
	</view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiGetConversations, apiCreateNewConversation, apiDeleteConversation } from '@/services/api'

const conversations = ref([])
const palette = { icon: 'rgba(27,31,42,.70)' }

async function fetchConversations() {
	try {
		const res = await apiGetConversations()
		conversations.value = Array.isArray(res?.data) ? res.data : []
	} catch (e) {
		console.error('fetchConversations error', e)
	}
}

onShow(() => { fetchConversations() })

async function createNewConversation() {
	try {
		const res = await apiCreateNewConversation()
		const newConversation = res?.data || {}
		if (newConversation.conversationId) {
			uni.navigateTo({ url: `/pages/chat/index?conversationId=${newConversation.conversationId}` })
		} else {
			fetchConversations()
		}
	} catch (e) {
		console.error('createNewConversation error', e)
	}
}

function goToConversation(c) { uni.navigateTo({ url: `/pages/chat/index?conversationId=${c.conversationId}` }) }
function goMySpace() { uni.navigateTo({ url: '/pages/profile/index' }) }
function formatDate(d) { try { return d ? new Date(d).toLocaleString() : '' } catch (e) { return '' } }

async function onDeleteConversation(c) {
	const conversationId = c?.conversationId
	if (!conversationId) return

	uni.showModal({
		title: '删除对话',
		content: '确定要删除该对话吗？删除后将从历史列表移除。',
		confirmText: '删除',
		confirmColor: '#e53935',
		success: async (result) => {
			if (!result?.confirm) return
			try {
				await apiDeleteConversation(conversationId)
				conversations.value = conversations.value.filter((x) => x.conversationId !== conversationId)
				uni.showToast({ title: '已删除', icon: 'none' })
			} catch (e) {
				console.error('delete conversation error', e)
				uni.showToast({ title: '删除失败', icon: 'none' })
			}
		},
	})
}

function onLongPressConversation(c) {
	// 长按触发删除（二次确认在 onDeleteConversation 内）
	onDeleteConversation(c)
}

const bottomBtnPrimaryStyle = { background: 'linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%)', border: 'none', width: '44%', height: '44px', boxShadow: '0 16px 30px rgba(78,205,196,.28)', fontWeight: '800' }
const bottomBtnGhostStyle = { background: 'rgba(255,255,255,.86)', border: '1px solid rgba(27,31,42,.10)', width: '44%', height: '44px', fontWeight: '800', color: '#1b1f2a' }
</script>

<style scoped>
.page { height:100vh; padding:18px 16px; background: radial-gradient(900rpx 520rpx at 15% 8%, rgba(102,217,232,0.26), transparent 60%), radial-gradient(860rpx 520rpx at 85% 16%, rgba(78,205,196,0.22), transparent 58%), linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(245,251,251,1) 55%, rgba(255,255,255,1) 100%); overflow:hidden; }
.body{height:100vh; padding-top:10px; padding-bottom:96px; box-sizing:border-box}
.conversation-item{padding:12px 0;border-bottom:1px solid #eaeaea}
.title{font-size:16px;font-weight:800}
.last-message{font-size:14px;color:#666;margin-top:6px}
.timestamp{font-size:12px;color:#999;margin-top:6px}
.empty-wrap{height:calc(100vh - 140px);display:flex;flex-direction:column;align-items:center;justify-content:center}
.empty{text-align:center;color:#999;margin-bottom:16px}

.bottom-bar{position:fixed;left:0;right:0;bottom:0;z-index:99;padding:10px 16px calc(10px + env(safe-area-inset-bottom));display:flex;justify-content:space-between;gap:12px;background:rgba(255,255,255,.80);backdrop-filter:saturate(180%) blur(10px);border-top:1px solid rgba(27,31,42,.06)}
</style>
