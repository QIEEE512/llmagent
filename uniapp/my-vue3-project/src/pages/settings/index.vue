<template>
	<view class="page">
		<view class="title">设置</view>
		<view class="sub">待设计：偏好设置、通知、隐私、关于等</view>

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
	padding: 24px 6px 8px;
}

.sub {
	text-align: center;
	font-size: 13px;
	color: rgba(27, 31, 42, 0.55);
	padding: 0 6px;
}
</style>
