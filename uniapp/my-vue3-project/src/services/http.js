import { getToken, clearToken } from './storage'

// 来自 backend-apis/README.md
const API_ORIGIN = 'https://jkyhobdhqqah.sealoshzh.site'
const API_PREFIX = '/api'

function buildUrl(path) {
	// H5 开发期（localhost）用相对 /api 走 Vite proxy，避免浏览器 CORS 预检失败
	// 非 H5/生产仍直连线上域名
	const isH5Dev =
		typeof window !== 'undefined' &&
		typeof location !== 'undefined' &&
		/localhost|127\.0\.0\.1/.test(location.host)
	const base = isH5Dev ? API_PREFIX : API_ORIGIN + API_PREFIX
	if (!path) return base
	return base + (path.startsWith('/') ? path : `/${path}`)
}

function normalizeError(err) {
	// uni.request 失败时 err 结构不统一，这里尽量归一
	if (typeof err === 'string') return { message: err }
	if (!err) return { message: '网络错误' }
	return err
}

function isTimeoutError(err) {
	const msg = String(err?.errMsg || err?.message || '').toLowerCase()
	// 各端常见："request:fail timeout" / "timeout" / "request abort" 等
	return msg.includes('timeout')
}

export async function request({ method = 'GET', path, data, header, timeout = 15000 }) {
	return new Promise((resolve, reject) => {
		const url = buildUrl(path)
		const startedAt = Date.now()
		const token = getToken()
		const headers = {
			Accept: 'application/json',
			...(header || {}),
		}
		if (token) headers.Authorization = `Bearer ${token}`

		// 仅用于联调排查：打印最终 URL，便于确认是否走了 /api 前缀与 Vite proxy
		try {
			if (typeof window !== 'undefined' && /localhost|127\.0\.0\.1/i.test(location?.host || '')) {
				console.log('[http] request', method, url)
			}
		} catch (e) {
			// ignore
		}

		uni.request({
			url,
			method,
			data,
			header: headers,
			// H5 联调时后端/网关偶发慢响应，给更宽松的默认超时；调用方仍可通过 opts 覆盖
			timeout: timeout || 60000,
			success(res) {
				try {
					if (typeof window !== 'undefined' && /localhost|127\.0\.0\.1/i.test(location?.host || '')) {
						console.log('[http] response', method, url, res.statusCode, `+${Date.now() - startedAt}ms`)
					}
				} catch (e) {
					// ignore
				}
				const status = res.statusCode
				if (status === 401) {
					// FastAPI 默认结构：{ detail: '...' }
					clearToken()
					reject({ status, data: res.data, message: res.data?.detail || '未登录或登录已过期' })
					return
				}

				if (status !== 200) {
					reject({ status, data: res.data, message: res.data?.detail || res.data?.message || `请求失败(${status})` })
					return
				}

				// 业务成功：ApiResponse
				if (res.data && res.data.ok === true) {
					resolve(res.data)
					return
				}

				// 业务失败（当前阶段后端不一定返回 ok=false，这里兜底）
				reject({ status, data: res.data, message: res.data?.message || res.data?.detail || '请求失败' })
			},
			fail(err) {
				try {
					if (typeof window !== 'undefined' && /localhost|127\.0\.0\.1/i.test(location?.host || '')) {
						console.log('[http] fail', method, url, err?.errMsg || err)
					}
				} catch (e) {
					// ignore
				}
				const isGen = typeof path === 'string' && path.startsWith('/avatar/generate')
				const friendly = isGen && isTimeoutError(err) ? '生成时间较长，请稍后重试' : err?.errMsg || '网络错误'
				reject({ status: 0, ...normalizeError(err), message: friendly })
			},
		})
	})
}

export async function get(path, params, opts) {
	return request({ method: 'GET', path, data: params, ...(opts || {}) })
}

export async function post(path, data, opts) {
	return request({ method: 'POST', path, data, ...(opts || {}) })
}

export async function upload({ path, filePath, name = 'file', formData, header, timeout = 30000 }) {
	return new Promise((resolve, reject) => {
		const url = buildUrl(path)
		const startedAt = Date.now()
		const token = getToken()
		const headers = { ...(header || {}) }
		if (token) headers.Authorization = `Bearer ${token}`

		try {
			if (typeof window !== 'undefined' && /localhost|127\.0\.0\.1/i.test(location?.host || '')) {
				console.log('[http] upload', url, 'name=', name, 'filePath=', filePath)
			}
		} catch (e) {
			// ignore
		}

		uni.uploadFile({
			url,
			filePath,
			name,
			formData,
			header: headers,
			timeout: timeout || 60000,
			success(res) {
				try {
					if (typeof window !== 'undefined' && /localhost|127\.0\.0\.1/i.test(location?.host || '')) {
						console.log('[http] upload response', url, res.statusCode, `+${Date.now() - startedAt}ms`)
					}
				} catch (e) {
					// ignore
				}
				const status = res.statusCode
				let data
				try {
					data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
				} catch (e) {
					data = res.data
				}

				if (status === 401) {
					clearToken()
					reject({ status, data, message: data?.detail || '未登录或登录已过期' })
					return
				}
				if (status !== 200) {
					reject({ status, data, message: data?.detail || data?.message || `上传失败(${status})` })
					return
				}
				if (data && data.ok === true) {
					resolve(data)
					return
				}
				reject({ status, data, message: data?.message || data?.detail || '上传失败' })
			},
			fail(err) {
				try {
					if (typeof window !== 'undefined' && /localhost|127\.0\.0\.1/i.test(location?.host || '')) {
						console.log('[http] upload fail', url, err?.errMsg || err)
					}
				} catch (e) {
					// ignore
				}
				reject({ status: 0, ...normalizeError(err), message: err?.errMsg || '上传失败' })
			},
		})
	})
}
