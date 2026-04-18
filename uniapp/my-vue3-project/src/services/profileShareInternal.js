// Internal helpers for profileShare.js
// Keep this separated to avoid circular deps with http.js

// Mirror src/services/http.js constants
const API_ORIGIN = 'https://jkyhobdhqqah.sealoshzh.site'
const API_PREFIX = '/api'

function isH5Dev() {
	try {
		return (
			typeof window !== 'undefined' &&
			typeof location !== 'undefined' &&
			/localhost|127\.0\.0\.1/.test(location.host)
		)
	} catch (e) {
		return false
	}
}

// This returns the base url used by request layer, like:
// - H5 dev: /api
// - prod/native: https://xxx.com/api
export function __internal_getApiBaseUrl() {
	return isH5Dev() ? API_PREFIX : API_ORIGIN + API_PREFIX
}
