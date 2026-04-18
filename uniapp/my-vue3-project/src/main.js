import {
	createSSRApp
} from "vue";
import App from "./App.vue";

// uView Plus（ESM 引入，避免 H5 下 require 失败导致组件不渲染）
import uviewPlus from 'uview-plus'

// 兜底：若自动注册失效，仅手动注册本项目用到的少量组件
import UIcon from 'uview-plus/components/u-icon/u-icon.vue'
import UButton from 'uview-plus/components/u-button/u-button.vue'
import UCard from 'uview-plus/components/u-card/u-card.vue'
import UInput from 'uview-plus/components/u-input/u-input.vue'
import UToast from 'uview-plus/components/u-toast/u-toast.vue'

export function createApp() {
	const app = createSSRApp(App);
	// uView Plus 安装：Vue3 下 install 的入参是 app 实例
	app.use(uviewPlus)

	// 若仍出现 "Failed to resolve component: u-xxx"，可依赖此兜底注册
	app.component('u-icon', UIcon)
	app.component('u-button', UButton)
	app.component('u-card', UCard)
	app.component('u-input', UInput)
	app.component('u-toast', UToast)
	return {
		app,
	};
}
