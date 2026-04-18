<template>
	<view class="page">
		<view class="card">
			<view class="card-title">已保存的成长档案</view>
			<view class="card-sub">这里展示你点击“保存到档案”的所有故事</view>
		</view>

		<view class="card">
			<view class="toolbar">
				<u-button type="default" shape="circle" :customStyle="ghostBtnStyle" :loading="loading" @click="fetchList">
					刷新
				</u-button>
				<u-button type="primary" shape="circle" :customStyle="ghostPrimaryBtnStyle" @click="goGenerate">
					去生成
				</u-button>
			</view>

			<view v-if="loading" class="muted">正在加载…</view>
			<view v-else>
				<view v-if="!items.length" class="muted">还没有保存过档案，去“成长档案”生成并保存一次吧</view>
				<view v-else class="list">
					<view v-for="it in items" :key="it.storyId" class="item" @click="openDetail(it.storyId)">
						<view class="item-hd">
							<view class="item-title">{{ it.title || '未命名故事' }}</view>
							<view class="item-actions" @click.stop>
								<u-button
									type="default"
									shape="circle"
									:size="miniBtnSize"
									:customStyle="miniGhostBtnStyle"
									@click="confirmDelete(it.storyId)"
								>
									删除
								</u-button>
							</view>
						</view>
						<view class="item-sub">保存时间：{{ formatDate(it.savedAt) }}</view>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { onShow } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { apiDeleteProfileStory, apiListProfileStories } from '@/services/api'

const items = ref([])
const loading = ref(false)

onShow(() => {
	fetchList()
})

async function fetchList() {
	loading.value = true
	try {
		const res = await apiListProfileStories({ page: 1, pageSize: 50 })
		const data = res?.data
		const list = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
		items.value = list
	} catch (e) {
		console.error('list stories error', e)
		items.value = []
		const status = Number(e?.status || e?.statusCode)
		if (status === 401) {
			uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
		} else if (status === 404) {
			uni.showToast({ title: '当前账号下暂无档案', icon: 'none' })
		} else {
			uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
		}
	} finally {
		loading.value = false
	}
}

function openDetail(storyId) {
	uni.navigateTo({ url: `/pages/profile-story-detail/index?storyId=${encodeURIComponent(storyId)}` })
}

function goGenerate() {
	uni.navigateTo({ url: '/pages/profile-story/index' })
}

function confirmDelete(storyId) {
	uni.showModal({
		title: '删除档案',
		content: '确定要删除这条成长档案吗？删除后不可恢复。',
		success: async (r) => {
			if (!r.confirm) return
			await doDelete(storyId)
		},
	})
}

async function doDelete(storyId) {
	try {
		await apiDeleteProfileStory(storyId)
		items.value = items.value.filter(x => x.storyId !== storyId)
		uni.showToast({ title: '已删除', icon: 'none' })
	} catch (e) {
		console.error('delete story error', e)
		uni.showToast({ title: '删除失败', icon: 'none' })
	}
}

function formatDate(d) {
	try {
		return d ? new Date(d).toLocaleString() : ''
	} catch (e) {
		return ''
	}
}

const miniBtnSize = 'mini'

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

const miniGhostBtnStyle = {
	background: 'rgba(255,255,255,.86)',
	border: '1px solid rgba(27,31,42,.10)',
	height: '28px',
	paddingLeft: '10px',
	paddingRight: '10px',
	fontWeight: '800',
	color: '#1b1f2a',
	fontSize: '12px',
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

.toolbar {
	display: flex;
	gap: 10px;
	justify-content: center;
	align-items: center;
	margin-bottom: 12px;
}

.list {
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.item {
	padding: 12px 12px;
	border-radius: 14px;
	border: 1px solid rgba(27, 31, 42, 0.08);
	background: rgba(255, 255, 255, 0.86);
}

.item-hd {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 10px;
}

.item-title {
	font-size: 15px;
	font-weight: 900;
	color: #1b1f2a;
	flex: 1;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-sub {
	margin-top: 6px;
	font-size: 12px;
	color: rgba(27, 31, 42, 0.55);
}

.muted {
	font-size: 13px;
	color: rgba(27, 31, 42, 0.55);
	text-align: center;
	padding: 14px 0;
}
</style>
