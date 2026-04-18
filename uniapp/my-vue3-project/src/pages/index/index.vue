<template>
  <!-- 兼容旧首页入口：复用 chat 主页面 -->
  <view class="wrap">
    <ChatHome />
  </view>
</template>

<script setup>
import ChatHome from '../chat/index.vue'
</script>

<style scoped>
.wrap {
  min-height: 100vh;
}
</style>
