import { useState } from 'react'
import ToggleSwitch, { type Option } from '../components/ToggleSwitch'
import { runSearch, type SearchMode, type SearchPromptResult } from '../lib/searchPrompt'

const MODES: Option[] = [
  { value: 'search', label: 'Search' },
  { value: 'chat', label: 'Chat' },
];

export default function SearchPage() {
  const [mode, setMode] = useState<SearchMode>('search');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<SearchPromptResult | null>(null);
  const [streamed, setStreamed] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit() {
    const prompt = query.trim();
    if (!prompt || loading) return;
    setLoading(true);
    setResult(null);
    setStreamed('');
    setError('');
    try {
      const answer = await runSearch(prompt, mode, (token) => setStreamed((s) => s + token));
      setResult(answer);
      setStreamed('');
      setQuery('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  function switchMode(value: string) {
    setMode(value === 'chat' ? 'chat' : 'search');
    setResult(null);
    setStreamed('');
    setError('');
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
        <ToggleSwitch value={mode} options={MODES} onChange={switchMode} />
        <button type="submit" className="hidden" aria-hidden="true" tabIndex={-1}>
          Send
        </button>
      </form>

      <section className="min-h-56 px-5">
        {loading && mode === 'chat' ? (
          <pre className="whitespace-pre-wrap wrap-break-word font-sans text-body">
            {streamed || 'Working on it…'}
          </pre>
        ) : loading ? (
          <p className="text-muted">Working on it…</p>
        ) : error ? (
          <p className="text-red-600">{error}</p>
        ) : result?.mode === 'search' ? (
          result.hits.length === 0 ? (
            <p className="text-muted">No results found.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {result.hits.map((hit, i) => (
                <li key={`${hit.doc_id}-${i}`} className="rounded-lg border border-line bg-surface p-4">
                  <div className="flex items-baseline justify-between gap-3">
                    <h2 className="font-medium text-ink">{hit.title}</h2>
                    <span className="shrink-0 text-sm text-subtle">{hit.score.toFixed(3)}</span>
                  </div>
                  <p className="mt-1 text-xs text-subtle">
                    {[
                      hit.category,
                      hit.page != null ? `page ${hit.page}` : null,
                      hit.filename,
                    ].filter(Boolean).join(' · ')}
                  </p>
                  <p className="mt-2 whitespace-pre-wrap wrap-break-word text-body">{hit.text}</p>
                </li>
              ))}
            </ul>
          )
        ) : result?.mode === 'chat' ? (
          <div>
            <pre className="whitespace-pre-wrap wrap-break-word font-sans text-body">{result.answer}</pre>
            {result.sources.length > 0 && (
              <ul className="mt-4 flex flex-col gap-1 border-t border-line pt-3">
                <li className="text-xs uppercase tracking-wide text-subtle">Sources</li>
                {result.sources.map((source, i) => (
                  <li key={`${source.doc_id}-${i}`} className="text-sm text-subtle">
                    {source.title}
                    {source.page != null ? ` · page ${source.page}` : ''} · {source.score.toFixed(3)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <p className="text-muted">Results will show up here.</p>
        )}
      </section>
    </div>
  )
}
