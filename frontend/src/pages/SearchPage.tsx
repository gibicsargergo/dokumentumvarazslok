import { useState } from 'react'
import ToggleSwitch, { type Option } from '../components/ToggleSwitch'
import { runSearch, type SearchMode } from '../lib/searchStub'

const MODES: Option[] = [
  { value: 'search', label: 'Search' },
  { value: 'chat', label: 'Chat' },
];

export default function SearchPage() {
  const [mode, setMode] = useState<SearchMode>('search');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit() {
    const prompt = query.trim();
    if (!prompt) return;
    setLoading(true);
    setResult('');
    const answer = await runSearch(prompt, mode);
    setResult(answer);
    setQuery('');
    setLoading(false);
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-6 py-8">
      <header>
        <h1 className="mb-6 text-center text-3xl font-semibold tracking-tight text-ink">
          Document Vault
        </h1>
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
        className="flex items-center gap-3"
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          type="text"
          placeholder={mode === 'search' ? 'Search your documents…' : 'Ask about your documents…'}
          className="min-w-0 flex-1 rounded-full border border-line px-5 py-2.5 text-base text-ink outline-none transition focus:border-transparent focus:shadow-[0_1px_6px_rgba(0,0,0,0.2)]"
        />
        <ToggleSwitch
          value={mode}
          options={MODES}
          onChange={(value) => setMode(value === 'chat' ? 'chat' : 'search')}
        />
        <button type="submit" className="hidden" aria-hidden="true" tabIndex={-1}>
          Send
        </button>
      </form>

      <section className="min-h-56 px-5">
        {loading ? (
          <p className="text-muted">Working on it…</p>
        ) : result ? (
          <pre className="whitespace-pre-wrap wrap-break-word font-sans text-body">{result}</pre>
        ) : (
          <p className="text-muted">Results will show up here.</p>
        )}
      </section>
    </div>
  )
}
