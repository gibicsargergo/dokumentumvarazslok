// Calls to the FastAPI backend for the search page.
// Search mode POSTs to /api/search; chat mode talks to the /api/chat websocket.
export type SearchMode = 'search' | 'chat';

export type SearchHit = {
  text: string;
  score: number;
  bm25: number;
  fuzzy: number;
  cosine: number;
  title: string;
  category: string;
  tags: string[];
  page: number | null;
  page_end: number | null;
  source: string;
  filename: string;
  doc_id: string;
};

export type ChatSource = {
  title: string;
  page: number | null;
  doc_id: string;
  score: number;
};

export type SearchPromptResult =
  | { mode: 'search'; hits: SearchHit[] }
  | { mode: 'chat'; answer: string; sources: ChatSource[] };

export async function runSearch(
  prompt: string,
  mode: SearchMode,
  onToken?: (token: string) => void,
): Promise<SearchPromptResult> {
  if (mode === 'chat') {
    return askViaChat(prompt, onToken);
  }
  return searchDocuments(prompt);
}

async function searchDocuments(prompt: string): Promise<SearchPromptResult> {
  const res = await fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: prompt, k: 5 }),
  });
  if (!res.ok) {
    let detail = `Search failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // keep the generic message
    }
    throw new Error(detail);
  }
  const hits = (await res.json()) as SearchHit[];
  return { mode: 'search', hits };
}

function askViaChat(
  prompt: string,
  onToken?: (token: string) => void,
): Promise<SearchPromptResult> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(
      `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/chat`,
    );

    const sources: ChatSource[] = [];
    let answer = '';
    let settled = false;

    const finish = (value: SearchPromptResult) => {
      if (settled) return;
      settled = true;
      try { ws.close(); } catch { /* ignore */ }
      resolve(value);
    };

    const fail = (message: string) => {
      if (settled) return;
      settled = true;
      try { ws.close(); } catch { /* ignore */ }
      reject(new Error(message));
    };

    ws.onopen = () => {
      ws.send(prompt);
    };

    ws.onmessage = (event) => {
      let frame: { type?: string; content?: string; sources?: ChatSource[]; message?: string };
      try {
        frame = JSON.parse(event.data);
      } catch {
        return;
      }

      switch (frame?.type) {
        case 'sources':
          if (Array.isArray(frame.sources)) sources.push(...frame.sources);
          break;
        case 'token':
          if (typeof frame.content === 'string') {
            answer += frame.content;
            onToken?.(frame.content);
          }
          break;
        case 'end':
          finish({ mode: 'chat', answer, sources });
          break;
        case 'error':
          fail(frame.message ?? 'Chat error');
          break;
      }
    };

    ws.onerror = () => fail('Chat connection failed');
    ws.onclose = () => {
      if (settled) return;
      // Server closed the socket; keep whatever we collected.
      if (answer) finish({ mode: 'chat', answer, sources });
      else fail('Chat connection closed');
    };
  });
}
