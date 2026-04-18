// Profile Share helpers
// - shareUrl is relative path like /s/{shareId}/view
// - front-end must build full URL using a public backend origin

import { __internal_getApiBaseUrl } from './profileShareInternal'

function trimSlashEnd(s) {
	return typeof s === 'string' ? s.replace(/\/+$/, '') : ''
}

function ensureStartsWithSlash(p) {
	if (!p) return ''
	return p.startsWith('/') ? p : `/${p}`
}

function safeParseOrigin(url) {
	try {
		const u = new URL(url)
		return u.origin
	} catch (e) {
		return ''
	}
}

export function getPublicApiOrigin() {
	// 1) Prefer env: VITE_API_BASE_ORIGIN
	// Note: in uniapp+vite, import.meta.env works in H5. For app/miniapp, it might be undefined.
	const envOrigin = trimSlashEnd(import.meta?.env?.VITE_API_BASE_ORIGIN)
	if (envOrigin) return envOrigin

	// 2) Fallback: derive from current API baseUrl used by request layer
	const apiBaseUrl = __internal_getApiBaseUrl() // e.g. https://xx.com/api or /api
	const derived = safeParseOrigin(apiBaseUrl)
	if (derived) return derived

	// 3) Last fallback (H5): current location origin
	try {
		if (typeof location !== 'undefined' && location.origin) return location.origin
	} catch (e) {
		// ignore
	}

	return ''
}

export function buildShareFullUrl(shareUrl) {
	const origin = getPublicApiOrigin()
	const path = ensureStartsWithSlash(String(shareUrl || ''))
	return origin ? origin + path : path
}
