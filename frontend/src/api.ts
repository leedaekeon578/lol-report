export type Summary = {
  games: number
  wins: number
  losses: number
  win_rate: number | null
}

export type Game = {
  match_id: string
  champion: string
  win: boolean
  started_at: string
}

export type Report = {
  summary: Summary
  games: Game[]
  searched_matches: number
  rift_matches: number
  incomplete: boolean
  incomplete_message: string | null
}

const ERROR_CODES = [
  'INVALID_INPUT',
  'ACCOUNT_NOT_FOUND',
  'RATE_LIMITED',
  'KEY_EXPIRED',
  'OTHER_ERROR',
] as const

export type ErrorCode = (typeof ERROR_CODES)[number]

export type ApiError = { code: ErrorCode; message: string }

export type FetchResult =
  | { ok: true; report: Report }
  | { ok: false; error: ApiError }

// 응답이 JSON 이 아니거나 네트워크가 실패하면 서버의 OTHER_ERROR 와 같은 문구를 쓴다 (D-011).
export const FALLBACK_ERROR: ApiError = {
  code: 'OTHER_ERROR',
  message: '조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.',
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isSummary(value: unknown): value is Summary {
  return (
    isRecord(value) &&
    typeof value.games === 'number' &&
    typeof value.wins === 'number' &&
    typeof value.losses === 'number' &&
    (value.win_rate === null || typeof value.win_rate === 'number')
  )
}

function isGame(value: unknown): value is Game {
  return (
    isRecord(value) &&
    typeof value.match_id === 'string' &&
    typeof value.champion === 'string' &&
    typeof value.win === 'boolean' &&
    typeof value.started_at === 'string'
  )
}

function isReport(value: unknown): value is Report {
  return (
    isRecord(value) &&
    isSummary(value.summary) &&
    Array.isArray(value.games) &&
    value.games.every(isGame) &&
    typeof value.searched_matches === 'number' &&
    typeof value.rift_matches === 'number' &&
    typeof value.incomplete === 'boolean' &&
    (value.incomplete_message === null ||
      typeof value.incomplete_message === 'string')
  )
}

function readApiError(body: unknown): ApiError | null {
  if (!isRecord(body) || !isRecord(body.error)) return null
  const { code, message } = body.error
  if (typeof message !== 'string') return null
  const known = ERROR_CODES.find((candidate) => candidate === code)
  if (known === undefined) return null
  // 서버가 준 code 와 message 외의 값은 버린다.
  return { code: known, message }
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function fetchReport(
  riotId: string,
  fetchFn: typeof fetch = fetch,
): Promise<FetchResult> {
  try {
    const response = await fetchFn('/api/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ riot_id: riotId }),
    })
    const body = await readJson(response)
    if (response.ok) {
      return isReport(body)
        ? { ok: true, report: body }
        : { ok: false, error: FALLBACK_ERROR }
    }
    return { ok: false, error: readApiError(body) ?? FALLBACK_ERROR }
  } catch {
    // 예외 원문은 화면에도 로그에도 내보내지 않는다.
    return { ok: false, error: FALLBACK_ERROR }
  }
}
