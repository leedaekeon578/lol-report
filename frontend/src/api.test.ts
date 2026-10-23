import assert from 'node:assert/strict'
import { test } from 'node:test'
import { FALLBACK_ERROR, fetchReport } from './api.ts'

const REPORT = {
  summary: { games: 1, wins: 1, losses: 0, win_rate: 100.0 },
  games: [
    {
      match_id: 'KR_1',
      champion: 'Ahri',
      win: true,
      started_at: '2023-11-14T22:13:20Z',
    },
  ],
  searched_matches: 3,
  rift_matches: 3,
  incomplete: true,
  incomplete_message: '협곡 매치를 20개 채우지 못했습니다. 조회한 3개 중 협곡 매치는 3개입니다.',
}

type Captured = { url: string; init: RequestInit | undefined }

function fakeFetch(respond: () => Response | Promise<Response>, captured?: Captured[]): typeof fetch {
  return (async (input: RequestInfo | URL, init?: RequestInit) => {
    captured?.push({ url: String(input), init })
    return respond()
  }) as typeof fetch
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

test('성공 응답을 그대로 돌려주고 POST /api/report 로 요청한다', async () => {
  const captured: Captured[] = []
  const result = await fetchReport('Name#KR1', fakeFetch(() => json(200, REPORT), captured))
  assert.deepEqual(result, { ok: true, report: REPORT })
  assert.equal(captured.length, 1)
  assert.equal(captured[0].url, '/api/report')
  assert.equal(captured[0].init?.method, 'POST')
  assert.deepEqual(captured[0].init?.headers, { 'Content-Type': 'application/json' })
  assert.deepEqual(JSON.parse(String(captured[0].init?.body)), { riot_id: 'Name#KR1' })
})

test('win_rate 가 null 인 응답도 받는다', async () => {
  const empty = {
    ...REPORT,
    summary: { games: 0, wins: 0, losses: 0, win_rate: null },
    games: [],
    incomplete: false,
    incomplete_message: null,
  }
  const result = await fetchReport('Name#KR1', fakeFetch(() => json(200, empty)))
  assert.deepEqual(result, { ok: true, report: empty })
})

const SERVER_ERRORS = [
  [400, 'INVALID_INPUT', '닉네임#태그 형식으로 입력해 주세요.'],
  [404, 'ACCOUNT_NOT_FOUND', '해당 닉네임#태그의 계정을 찾을 수 없습니다.'],
  [429, 'RATE_LIMITED', 'Riot API 호출 한도를 넘어 조회를 멈췄습니다. 잠시 후 다시 시도해 주세요.'],
  [502, 'KEY_EXPIRED', 'Riot API 키가 만료되었거나 유효하지 않습니다. 서버 키를 갱신해야 합니다.'],
  [502, 'OTHER_ERROR', '조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.'],
] as const

for (const [status, code, message] of SERVER_ERRORS) {
  test(`오류 ${status} ${code}: 서버의 code 와 message 를 그대로 전달한다`, async () => {
    const result = await fetchReport(
      'Name#KR1',
      fakeFetch(() => json(status, { error: { code, message } })),
    )
    assert.deepEqual(result, { ok: false, error: { code, message } })
  })
}

test('오류 본문의 다른 필드는 버린다', async () => {
  const result = await fetchReport(
    'Name#KR1',
    fakeFetch(() =>
      json(502, { error: { code: 'OTHER_ERROR', message: '고정 문구', detail: 'SECRET-DETAIL' } }),
    ),
  )
  assert.deepEqual(result, { ok: false, error: { code: 'OTHER_ERROR', message: '고정 문구' } })
  assert.ok(!JSON.stringify(result).includes('SECRET-DETAIL'))
})

test('JSON 이 아닌 오류 응답은 OTHER_ERROR 문구로 바꾼다', async () => {
  const result = await fetchReport(
    'Name#KR1',
    fakeFetch(() => new Response('Bad Gateway', { status: 502 })),
  )
  assert.deepEqual(result, { ok: false, error: FALLBACK_ERROR })
  assert.equal(FALLBACK_ERROR.code, 'OTHER_ERROR')
})

test('알 수 없는 code 는 OTHER_ERROR 문구로 바꾼다', async () => {
  const result = await fetchReport(
    'Name#KR1',
    fakeFetch(() => json(500, { error: { code: 'WHATEVER', message: '알 수 없음' } })),
  )
  assert.deepEqual(result, { ok: false, error: FALLBACK_ERROR })
})

test('200 이어도 모양이 다르면 OTHER_ERROR 문구로 바꾼다', async () => {
  const result = await fetchReport('Name#KR1', fakeFetch(() => json(200, { summary: {} })))
  assert.deepEqual(result, { ok: false, error: FALLBACK_ERROR })
})

test('fetch 예외는 OTHER_ERROR 문구로 바꾸고 예외 원문을 담지 않는다', async () => {
  const result = await fetchReport(
    'Name#KR1',
    fakeFetch(() => {
      throw new TypeError('boom DUMMY-SECRET-0000')
    }),
  )
  assert.deepEqual(result, { ok: false, error: FALLBACK_ERROR })
  assert.ok(!JSON.stringify(result).includes('DUMMY-SECRET-0000'))
})
