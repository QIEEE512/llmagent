<template>
	<view class="page">
		<view class="title">更多</view>
		<view class="sub">待设计：账号管理 / 设置</view>

		<view class="card">
			<view class="item" @click="goAccount">
				<view class="left">
					<view class="dot"></view>
					<text class="name">账号管理</text>
				</view>
				<u-icon name="arrow-right" size="16" color="rgba(27,31,42,.45)" />
			</view>

			<view class="line"></view>

			<view class="item" @click="goSettings">
				<view class="left">
					<view class="dot dot2"></view>
					<text class="name">设置</text>
				</view>
				<u-icon name="arrow-right" size="16" color="rgba(27,31,42,.45)" />
			</view>
		</view>

		<u-button type="primary" shape="circle" :customStyle="btnStyle" @click="goBack">返回</u-button>
	</view>
</template>

<script setup>
const btnStyle = {
	background: 'linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%)',
	border: 'none',
	width: '160px',
	height: '44px',
	marginTop: '18px',
	boxShadow: '0 16px 30px rgba(78, 205, 196, .28)',
	fontWeight: '800',
}

function goAccount() {
	uni.navigateTo({ url: '/pages/account/index' })
}

function goSettings() {
	uni.navigateTo({ url: '/pages/settings/index' })
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

.title {
	text-align: center;
	font-size: 20px;
	font-weight: 900;
	color: #1b1f2a;
	padding: 18px 6px 6px;
}

.sub {
	text-align: center;
	font-size: 13px;
	color: rgba(27, 31, 42, 0.55);
	padding: 0 6px 14px;
}

.card {
	background: rgba(255, 255, 255, 0.92);
	border: 1px solid rgba(27, 31, 42, 0.08);
	border-radius: 18px;
	overflow: hidden;
	box-shadow: 0 22px 42px rgba(20, 27, 61, 0.12);
}

.item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 14px 14px;
}

.left {
	display: flex;
	align-items: center;
	gap: 10px;
}

.dot {
	width: 10px;
	height: 10px;
	border-radius: 999px;
	background: linear-gradient(180deg, #4ECDC4 0%, #66D9E8 100%);
	box-shadow: 0 10px 18px rgba(78, 205, 196, 0.22);
}

.dot2 {
	background: linear-gradient(180deg, #66D9E8 0%, #88E6FF 100%);
}

.name {
	font-size: 15px;
	font-weight: 800;
	color: #1b1f2a;
}

.line {
	height: 1px;
	background: rgba(27, 31, 42, 0.06);
}
</style>
