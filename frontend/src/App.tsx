import { useRef, useState } from 'react'
import { fetchReport } from './api.ts'
import type { ApiError, Report } from './api.ts'
import GameList from './components/GameList.tsx'
import Notice from './components/Notice.tsx'
import SearchForm from './components/SearchForm.tsx'
import SummaryView from './components/SummaryView.tsx'
import { describeEmpty } from './format.ts'

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; report: Report }
  | { status: 'error'; error: ApiError }

function Result({ report }: { report: Report }) {
  const noGames = report.games.length === 0
  return (
    <>
      <SummaryView summary={report.summary} />
      {noGames ? (
        <Notice kind="empty" title="해당 게임이 없습니다.">
          {describeEmpty(report.rift_matches, report.searched_matches)}
        </Notice>
      ) : null}
      {report.incomplete && report.incomplete_message ? (
        <Notice kind="info">{report.incomplete_message}</Notice>
      ) : null}
      {noGames ? null : <GameList games={report.games} />}
    </>
  )
}

function App() {
  const [riotId, setRiotId] = useState('')
  const [state, setState] = useState<State>({ status: 'idle' })
  const inFlight = useRef(false)

  async function submit() {
    // 조회 중에는 제출 핸들러에서도 호출을 막는다 (버튼 비활성화와 별개).
    if (inFlight.current || riotId.trim() === '') return
    inFlight.current = true
    setState({ status: 'loading' }) // 이전 결과를 지운다.
    try {
      const result = await fetchReport(riotId)
      setState(
        result.ok
          ? { status: 'success', report: result.report }
          : { status: 'error', error: result.error },
      )
    } finally {
      inFlight.current = false
    }
  }

  return (
    <main>
      <h1>LoL Report</h1>
      <p className="lead">
        닉네임#태그를 입력하면 최근 소환사의 협곡 20매치 중 내 팀이 퍼스트블러드를 한 게임의 승 · 패 · 승률을 보여
        줍니다. (KR)
      </p>
      <section aria-label="입력">
        <SearchForm
          value={riotId}
          loading={state.status === 'loading'}
          onChange={setRiotId}
          onSubmit={submit}
        />
      </section>
      <section aria-label="결과" aria-live="polite">
        {state.status === 'loading' ? <Notice kind="loading">조회 중…</Notice> : null}
        {state.status === 'error' ? <Notice kind="error">{state.error.message}</Notice> : null}
        {state.status === 'success' ? <Result report={state.report} /> : null}
      </section>
    </main>
  )
}

export default App
