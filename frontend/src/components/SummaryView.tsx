import type { Summary } from '../api.ts'
import { formatWinRate } from '../format.ts'

function SummaryView({ summary }: { summary: Summary }) {
  return (
    <dl className="summary" aria-label="요약">
      <div>
        <dt>게임 수</dt>
        <dd>{summary.games}</dd>
      </div>
      <div>
        <dt>승</dt>
        <dd>{summary.wins}</dd>
      </div>
      <div>
        <dt>패</dt>
        <dd>{summary.losses}</dd>
      </div>
      <div>
        <dt>승률</dt>
        <dd>{formatWinRate(summary.win_rate)}</dd>
      </div>
    </dl>
  )
}

export default SummaryView
