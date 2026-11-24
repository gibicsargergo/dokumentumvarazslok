from typing import AsyncGenerator, List, Dict, Any
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from .config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE
)

# OpenAI kompatibilis kliens inicializálása
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL if OPENAI_BASE_URL else None
)

SYSTEM_PROMPT_TEMPLATE = (
    "Szigorúan csak a megadott kontextusból válaszolj a felhasználó kérdésére!"
    "Ha a kontextus nem tartalmaz elég információt a válaszhoz, egyértelműen jelezd, hogy nem tudod a választ.\n\n"
    "Kontextus:\n{context}"
)

def build_context_string(hits: List[Dict[str, Any]]) -> str:
    '''A keresési találatokból strukturált kontextus szöveget épít.'''
    context_blocks = []
    for h in hits:
        page_info = f" (oldal: {h['page']})" if h.get("page") is not None else ""
        block = f"--- Dokumentum: {h['title']}{page_info} ---\\n{h['text']}"
        context_blocks.append(block)
    return "\\n\\n".join(context_blocks)

async def stream_rag_response(query: str, hits: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    '''Lefuttatja az LLM hívást és tokenenként adja vissza a választ.'''
    context_str = build_context_string(hits)
    system_content = SYSTEM_PROMPT_TEMPLATE.format(context=context_str)

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": query}
    ]
    
    response_stream = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        stream=True,
        temperature=LLM_TEMPERATURE
    )
    
    async for chunk in response_stream:
        for choice in chunk.choices:
            content = choice.delta.content
            if content:
                yield content
