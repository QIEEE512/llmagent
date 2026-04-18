const USER_PROFILE_KEY = 'user_profile_v1'

export function getDefaultUserProfile() {
	return {
		name: '',
		learningGoal: '',
		preferences: '',
	}
}

export function getUserProfile() {
	try {
		const raw = uni.getStorageSync(USER_PROFILE_KEY)
		if (!raw) return getDefaultUserProfile()
		if (typeof raw === 'string') {
			try {
				const parsed = JSON.parse(raw)
				return { ...getDefaultUserProfile(), ...(parsed || {}) }
			} catch (e) {
				return { ...getDefaultUserProfile(), name: String(raw) }
			}
		}
		return { ...getDefaultUserProfile(), ...(raw || {}) }
	} catch (e) {
		return getDefaultUserProfile()
	}
}

export function setUserProfile(profile) {
	try {
		const next = { ...getDefaultUserProfile(), ...(profile || {}) }
		uni.setStorageSync(USER_PROFILE_KEY, next)
		return next
	} catch (e) {
		return { ...getDefaultUserProfile(), ...(profile || {}) }
	}
}

export function updateUserProfile(patch) {
	const current = getUserProfile()
	return setUserProfile({ ...current, ...(patch || {}) })
}
