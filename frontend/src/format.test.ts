import assert from 'node:assert/strict'
import { test } from 'node:test'
import { describeEmpty, formatStartedAt, formatWinRate } from './format.ts'

test('formatStartedAt: UTC ISO 를 한국 시간 YYYY-MM-DD HH:mm 으로 바꾼다', () => {
  assert.equal(formatStartedAt('2023-11-14T22:13:20Z'), '2023-11-15 07:13')
})

test('formatStartedAt: 자정 전후와 날짜 경계', () => {
  assert.equal(formatStartedAt('2023-11-14T14:59:00Z'), '2023-11-14 23:59')
  assert.equal(formatStartedAt('2023-11-14T15:00:00Z'), '2023-11-15 00:00')
})

test('formatStartedAt: 시간대 표기가 달라도 같은 순간이면 같은 결과', () => {
  assert.equal(formatStartedAt('2023-11-15T07:13:20+09:00'), '2023-11-15 07:13')
})

test('formatStartedAt: 잘못된 값은 "-"', () => {
  assert.equal(formatStartedAt('not-a-date'), '-')
  assert.equal(formatStartedAt(''), '-')
})

test('formatWinRate: 소수점 첫째 자리, null 이면 "-"', () => {
  assert.equal(formatWinRate(66.7), '66.7%')
  assert.equal(formatWinRate(100), '100.0%')
  assert.equal(formatWinRate(0), '0.0%')
  assert.equal(formatWinRate(null), '-')
})

test('describeEmpty: 새 기준(내 팀 퍼스트블러드)과 두 매치 수를 담는다', () => {
  assert.equal(
    describeEmpty(20, 25),
    '조회한 협곡 매치 20개(상세 조회 25개) 중 내 팀이 퍼스트블러드를 한 게임이 없습니다.',
  )
  assert.ok(!describeEmpty(3, 3).includes('직접'))
})
