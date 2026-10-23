type Props = {
  value: string
  loading: boolean
  onChange: (value: string) => void
  onSubmit: () => void
}

function SearchForm({ value, loading, onChange, onSubmit }: Props) {
  return (
    <form
      className="search"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
      }}
    >
      <label htmlFor="riot-id">닉네임#태그</label>
      <div className="search-row">
        <input
          id="riot-id"
          type="text"
          value={value}
          placeholder="예: Name#KR1"
          autoComplete="off"
          spellCheck={false}
          onChange={(event) => onChange(event.target.value)}
        />
        <button type="submit" disabled={loading || value.trim() === ''}>
          조회
        </button>
      </div>
    </form>
  )
}

export default SearchForm
