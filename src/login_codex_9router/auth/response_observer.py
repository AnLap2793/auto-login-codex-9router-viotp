import asyncio
from urllib.parse import urlsplit

from playwright.async_api import Page, Response

from .errors import AuthSignal, classify_response


_ALLOWED_HOST_SUFFIXES = ("openai.com", "auth0.com")
_SAFE_FIELDS = ("code", "type", "message")


class ResponseObserver:
    def __init__(self, page: Page) -> None:
        self._signals: asyncio.Queue[AuthSignal] = asyncio.Queue()
        self._tasks: set[asyncio.Task[None]] = set()
        self._active = False
        page.on("response", self._on_response)

    def _on_response(self, response: Response) -> None:
        if not self._active:
            return
        task = asyncio.create_task(self._inspect(response))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _inspect(self, response: Response) -> None:
        if response.status < 400 or response.request.resource_type not in {"fetch", "xhr", "document"}:
            return
        host = (urlsplit(response.url).hostname or "").lower()
        if not any(host == suffix or host.endswith(f".{suffix}") for suffix in _ALLOWED_HOST_SUFFIXES):
            return
        values: list[str] = []
        content_type = response.headers.get("content-type", "").lower()
        raw_length = response.headers.get("content-length", "")
        content_length = int(raw_length) if raw_length.isdigit() else None
        if "application/json" in content_type and (content_length is None or 0 < content_length <= 32_768):
            try:
                payload = await response.json()
                if isinstance(payload, dict):
                    values.extend(self._safe_values(payload))
                    error = payload.get("error")
                    if isinstance(error, dict):
                        values.extend(self._safe_values(error))
            except Exception:
                pass
        if "text/html" in content_type and response.status in {401, 403}:
            return
        signal = classify_response(response.status, tuple(values))
        if signal:
            self._signals.put_nowait(signal)

    @staticmethod
    def _safe_values(payload: dict[object, object]) -> list[str]:
        return [str(payload[key])[:200] for key in _SAFE_FIELDS if key in payload and isinstance(payload[key], str)]

    def start_step(self) -> None:
        self.clear()
        self._active = True

    def stop_step(self) -> None:
        self._active = False

    def clear(self) -> None:
        while not self._signals.empty():
            self._signals.get_nowait()

    def latest(self) -> AuthSignal | None:
        signal = None
        while not self._signals.empty():
            signal = self._signals.get_nowait()
        return signal
