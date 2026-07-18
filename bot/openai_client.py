from collections.abc import AsyncIterator

from openai import AsyncOpenAI


class OpenAIStreamer:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def stream_reply(
        self, system_prompt: str, history: list[dict]
    ) -> AsyncIterator[str]:
        stream = await self._client.responses.create(
            model=self._model,
            instructions=system_prompt,
            input=history,
            tools=[{"type": "web_search_preview"}],
            stream=True,
        )
        async for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
