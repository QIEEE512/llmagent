<template>
	<view class="page">
		<view class="hd">
			<view class="title">个人档案</view>
			<view class="sub">在这里维护你的基础资料，用于生成成长档案</view>
		</view>

		<view class="card" aria-label="我的资料">
			<view class="card-hd">
				<view class="card-title nowrap">我的资料</view>
				<u-button type="default" shape="circle" :customStyle="editBtnStyle" @tap="toggleEdit">{{ isEditing ? '保存' : '编辑' }}</u-button>
			</view>
			<view class="field">
				<view class="label">姓名</view>
				<view v-if="!isEditing" class="value-text">{{ displayText(form.name) }}</view>
				<u-input v-else v-model="form.name" placeholder="例如：小明" border="none" :customStyle="inputStyle" />
			</view>
			<view class="field">
				<view class="label">学习目标</view>
				<view v-if="!isEditing" class="value-text">{{ displayText(form.learningGoal) }}</view>
				<u-input v-else v-model="form.learningGoal" placeholder="例如：每天进步一点点" border="none" :customStyle="inputStyle" />
			</view>
			<view class="field">
				<view class="label">学习偏好</view>
				<view v-if="!isEditing" class="value-text value-text-multi">{{ displayText(form.preferences) }}</view>
				<u-input
					v-else
					v-model="form.preferences"
					type="textarea"
					autoHeight
					:maxlength="200"
					:showConfirmBar="false"
					placeholder="例如：科学、语文、英语（可用逗号/顿号分隔）"
					border="none"
					:customStyle="textareaStyle"
				/>
			</view>
		</view>

		<view class="card" style="margin-top:12px;">
			<view class="row" style="border-bottom:none; padding:10px 6px;">
				<text class="label">成长档案</text>
				<text class="value">从对话生成故事档案</text>
			</view>
			<view style="display:flex; flex-direction:column; gap:10px; padding: 0 6px 4px;">
				<u-button type="primary" shape="circle" :customStyle="btnStyleWide" @click="goStory">
					去生成（成长档案）
				</u-button>
				<u-button type="default" shape="circle" :customStyle="btnStyleWideGhost" @click="goStories">
					查看已保存档案
				</u-button>
			</view>
		</view>

		<u-button type="primary" shape="circle" :customStyle="btnStyle" @click="goBack">
			返回
		</u-button>
	</view>
</template>

<script setup>
import { reactive, ref } from 'vue'

import { getUserProfile, setUserProfile } from '@/services/userProfile'

const form = reactive({
	name: '',
	learningGoal: '',
	preferences: '',
})

const isEditing = ref(false)

try {
	Object.assign(form, getUserProfile())
} catch (e) {
	// ignore
}

const btnStyle = {
	background: 'linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%)',
	border: 'none',
	width: '160px',
	height: '44px',
	marginTop: '18px',
	boxShadow: '0 16px 30px rgba(78, 205, 196, .28)',
	fontWeight: '800',
}

const btnStyleWide = {
	...btnStyle,
	width: '260px',
	marginTop: '10px',
}

const btnStyleWideGhost = {
	background: 'rgba(255,255,255,.86)',
	border: '1px solid rgba(27,31,42,.10)',
	width: '260px',
	height: '44px',
	marginTop: '0px',
	boxShadow: '0 16px 30px rgba(20, 27, 61, .10)',
	fontWeight: '800',
	color: '#1b1f2a',
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

function goBack() {
	uni.navigateBack()
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

function displayText(v) {
	const s = String(v || '').trim()
	return s ? s : '未填写'
}

function save() {
	const next = {
		name: String(form.name || '').trim(),
		learningGoal: String(form.learningGoal || '').trim(),
		preferences: String(form.preferences || '').trim(),
	}
	setUserProfile(next)
	uni.showToast({ title: '已保存', icon: 'none' })
}

function toggleEdit() {
	if (isEditing.value) {
		save()
		isEditing.value = false
		return
	}
	isEditing.value = true
}

function goStory() {
	uni.navigateTo({ url: '/pages/profile-story/index' })
}

function goStories() {
	uni.navigateTo({ url: '/pages/profile-stories/index' })
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
	padding: 14px 6px 18px;
}

.title {
	font-size: 20px;
	font-weight: 900;
	color: #1b1f2a;
}

.sub {
	margin-top: 8px;
	font-size: 13px;
	color: rgba(27, 31, 42, 0.5);
}

.card {
	background: rgba(255, 255, 255, 0.92);
	border: 1px solid rgba(27, 31, 42, 0.08);
	border-radius: 18px;
	padding: 14px;
	box-shadow: 0 22px 42px rgba(20, 27, 61, 0.12);
}

.card-hd {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
	margin-bottom: 6px;
}

.card-title {
	font-size: 16px;
	font-weight: 900;
	color: #1b1f2a;
}

.nowrap {
	white-space: nowrap;
}

.field {
	padding: 10px 6px;
}

.actions {
	margin-top: 4px;
}

.row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 12px 6px;
	border-bottom: 1px solid rgba(27, 31, 42, 0.06);
}

.row:last-child {
	border-bottom: none;
}

.label {
	font-size: 14px;
	color: rgba(27, 31, 42, 0.55);
}

.value-text {
	font-size: 15px;
	font-weight: 800;
	color: #1b1f2a;
	padding: 8px 2px 2px;
}

.value-text-multi {
	line-height: 1.6;
	white-space: pre-wrap;
}

.value {
	font-size: 15px;
	font-weight: 800;
	color: #1b1f2a;
}
</style>
