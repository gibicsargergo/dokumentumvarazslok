// Temporary stand-in for the real backend.
// It simply echoes the prompt back. When the FastAPI endpoints exist, replace
// this body with a fetch/websocket call and nothing else needs to change.
export type SearchMode = 'search' | 'chat';

export async function runSearch(prompt: string, _mode: SearchMode): Promise<string> {
  await new Promise((resolve) => setTimeout(resolve, 200));
  return prompt;
}
