const COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
  '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52BE80',
  '#EC7063', '#5DADE2', '#58D68D', '#F4D03F', '#AF7AC5',
  '#85C1E9', '#F1948A', '#7FB3D3', '#76D7C4', '#F5B041'
]

export function getUserColor(userId: number): string {
  return COLORS[userId % COLORS.length]
}

export function truncateUserId(userId: number, length: number = 8): string {
  const idStr = userId.toString()
  if (idStr.length <= length) {
    return idStr
  }
  return idStr.substring(0, length)
}

