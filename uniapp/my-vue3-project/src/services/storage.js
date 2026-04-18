const TOKEN_KEY = 'auth_token'

export function getToken() {
	try {
		return uni.getStorageSync(TOKEN_KEY) || ''
	} catch (e) {
		return ''
	}
}

export function setToken(token) {
	try {
		uni.setStorageSync(TOKEN_KEY, token || '')
	} catch (e) {
		// ignore
	}
}

export function clearToken() {
	try {
		uni.removeStorageSync(TOKEN_KEY)
	} catch (e) {
		// ignore
	}
}
