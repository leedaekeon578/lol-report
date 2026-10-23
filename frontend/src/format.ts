// D-014: 한국 시간(Asia/Seoul)의 "YYYY-MM-DD HH:mm"
const seoulFormat = new Intl.DateTimeFormat('ko-KR', {
  timeZone: 'Asia/Seoul',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

export function formatStartedAt(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '-'
  const parts: Record<string, string> = {}
  for (const part of seoulFormat.formatToParts(date)) {
    parts[part.type] = part.value
  }
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`
}

// D-008: 소수점 첫째 자리. 승률이 없으면(게임 0개) "-"
export function formatWinRate(rate: number | null): string {
  return rate === null ? '-' : `${rate.toFixed(1)}%`
}

export function describeEmpty(riftMatches: number, searchedMatches: number): string {
  return `조회한 협곡 매치 ${riftMatches}개(상세 조회 ${searchedMatches}개) 중 내 팀이 퍼스트블러드를 한 게임이 없습니다.`
}
