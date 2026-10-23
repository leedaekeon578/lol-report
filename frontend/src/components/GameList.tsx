import type { Game } from '../api.ts'
import { formatStartedAt } from '../format.ts'

function GameList({ games }: { games: Game[] }) {
  return (
    <ul className="games" aria-label="게임 목록">
      {games.map((game) => (
        <li key={game.match_id}>
          <span className="champion">{game.champion}</span>
          <span className={game.win ? 'result win' : 'result loss'}>
            {game.win ? '승' : '패'}
          </span>
          <time dateTime={game.started_at}>{formatStartedAt(game.started_at)}</time>
        </li>
      ))}
    </ul>
  )
}

export default GameList
