"""FastAPI-сервер J.A.R.V.I.S.: чат-API + WebSocket + статический веб-UI."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from jarvis.core.brain import Brain
from jarvis.core.config import JarvisConfig, save_config
from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.utils import autostart
from jarvis.utils.logger import log
from jarvis.utils.paths import web_assets_dir


class WSManager:
    """Менеджер WebSocket-подключений (трансляция событий в UI)."""

    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.connections.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self.connections.discard(ws)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            dead: list[WebSocket] = []
            for ws in self.connections:
                try:
                    await ws.send_text(json.dumps(payload, ensure_ascii=False))
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.connections.discard(ws)


def create_app(
    brain: Brain,
    config: JarvisConfig,
    event_bus: EventBus,
    *,
    speaker: Any | None = None,
) -> FastAPI:
    """Создать FastAPI-приложение с подключённым мозгом."""
    app = FastAPI(title="Jarvis", version="0.2.0")
    ws_manager = WSManager()
    app.state.config = config
    app.state.brain = brain
    app.state.ws = ws_manager

    # Транслируем события мозга/скиллов в WS
    def relay(event_type: EventType, mk_payload: Any) -> None:
        async def handler(ev: Event) -> None:
            await ws_manager.broadcast(mk_payload(ev))
        event_bus.on(event_type, handler)

    relay(
        EventType.LLM_RESPONSE,
        lambda e: {"type": "assistant", "text": e.data.get("response", "")},
    )
    relay(
        EventType.SPEECH_RECOGNIZED,
        lambda e: {"type": "user_voice", "text": e.data.get("text", "")},
    )
    relay(
        EventType.SKILL_EXECUTE,
        lambda e: {"type": "skill", "skill": e.data.get("skill"), "args": e.data.get("args")},
    )
    relay(
        EventType.SKILL_RESULT,
        lambda e: {
            "type": "skill_result",
            "skill": e.data.get("skill"),
            "result": str(e.data.get("result", ""))[:500],
        },
    )
    relay(
        EventType.VOICE_STATUS,
        lambda e: {
            "type": "voice_status",
            "status": e.data.get("status", ""),
            "detail": e.data.get("detail", ""),
        },
    )
    relay(
        EventType.WAKE_WORD_DETECTED,
        lambda e: {
            "type": "wake_word",
            "word": e.data.get("word", ""),
        },
    )

    # ---------- HTTP API ----------

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        return {
            "ok": True,
            "name": config.name,
            "language": config.language,
            "voice_enabled": config.voice_enabled,
            "autostart": autostart.is_enabled(),
            "skills": list(brain.skills.keys()),
            "llm": {"provider": config.llm.provider, "model": config.llm.model},
        }

    @app.get("/api/config")
    async def get_config() -> dict[str, Any]:
        d = {
            "general": {
                "name": config.name,
                "master_name": config.master_name,
                "language": config.language,
                "voice_enabled": config.voice_enabled,
                "autostart": config.autostart,
                "wake_words": config.wake_words,
            },
            "llm": asdict(config.llm),
            "tts": asdict(config.tts),
            "stt": asdict(config.stt),
            "server": asdict(config.server),
        }
        d["llm"]["api_key"] = "***" if d["llm"]["api_key"] else ""
        return d

    @app.post("/api/config")
    async def update_config(data: dict[str, Any]) -> dict[str, Any]:
        general = data.get("general", {})
        if "name" in general:
            config.name = general["name"]
        if "master_name" in general:
            config.master_name = general["master_name"]
        if "voice_enabled" in general:
            config.voice_enabled = bool(general["voice_enabled"])
        if "autostart" in general:
            new_val = bool(general["autostart"])
            if new_val and not autostart.is_enabled():
                autostart.enable()
            elif not new_val and autostart.is_enabled():
                autostart.disable()
            config.autostart = new_val

        llm = data.get("llm", {})
        for key in ("provider", "model", "base_url", "temperature", "max_tokens"):
            if key in llm:
                setattr(config.llm, key, llm[key])
        if "api_key" in llm and llm["api_key"] and llm["api_key"] != "***":
            config.llm.api_key = llm["api_key"]

        tts = data.get("tts", {})
        for key in ("engine", "edge_voice", "edge_rate"):
            if key in tts:
                setattr(config.tts, key, tts[key])

        path = save_config(config)
        return {"ok": True, "saved_to": str(path)}

    @app.post("/api/chat")
    async def chat(payload: dict[str, Any]) -> dict[str, Any]:
        text = (payload.get("message") or "").strip()
        if not text:
            return JSONResponse({"error": "empty message"}, status_code=400)
        await ws_manager.broadcast({"type": "user", "text": text})
        response = await brain.think(text)
        if speaker is not None and config.voice_enabled:
            asyncio.create_task(speaker.speak(response))
        return {"response": response}

    @app.post("/api/reset")
    async def reset() -> dict[str, Any]:
        brain.reset_history()
        return {"ok": True}

    @app.get("/api/memory")
    async def get_memory() -> dict[str, Any]:
        return {"facts": brain.memory.all_facts()}

    @app.post("/api/memory")
    async def add_memory(payload: dict[str, Any]) -> dict[str, Any]:
        fact = (payload.get("fact") or "").strip()
        if not fact:
            return JSONResponse({"error": "empty"}, status_code=400)
        msg = brain.memory.add_fact(fact)
        return {"ok": True, "message": msg}

    @app.delete("/api/memory")
    async def del_memory(payload: dict[str, Any]) -> dict[str, Any]:
        fact = (payload.get("fact") or "").strip()
        if not fact:
            return JSONResponse({"error": "empty"}, status_code=400)
        msg = brain.memory.remove_fact(fact)
        return {"ok": True, "message": msg}

    # ---------- WebSocket ----------

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws_manager.connect(ws)
        await ws.send_text(json.dumps({
            "type": "hello",
            "name": config.name,
            "skills": list(brain.skills.keys()),
        }))
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send_text(json.dumps({"type": "error", "error": "bad json"}))
                    continue

                text = (data.get("message") or data.get("text") or "").strip()
                if not text:
                    continue
                await ws_manager.broadcast({"type": "user", "text": text})
                response = await brain.think(text)
                if speaker is not None and config.voice_enabled and data.get("speak", True):
                    asyncio.create_task(speaker.speak(response))
        except WebSocketDisconnect:
            pass
        except Exception as e:
            log.exception(f"WS ошибка: {e}")
        finally:
            await ws_manager.disconnect(ws)

    # ---------- Static UI ----------

    web_dir = web_assets_dir()
    if web_dir.exists():
        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(web_dir / "index.html")

        app.mount(
            "/static", StaticFiles(directory=str(web_dir)), name="static"
        )
    else:
        @app.get("/")
        async def index_placeholder() -> dict[str, str]:
            return {
                "message": (
                    "Jarvis API запущен. Web-UI не найден в "
                    f"{web_dir}. Используйте /ws или /api/chat."
                ),
            }

    return app


async def run_server(
    app: FastAPI, *, host: str = "127.0.0.1", port: int = 8765,
) -> None:
    """Запустить uvicorn внутри текущего event loop."""
    import uvicorn

    cfg = uvicorn.Config(
        app, host=host, port=port, log_level="warning", access_log=False,
    )
    server = uvicorn.Server(cfg)
    await server.serve()


def find_free_port(host: str, start: int = 8765, attempts: int = 30) -> int:
    """Найти свободный порт начиная со start."""
    import socket as _s

    for offset in range(attempts):
        p = start + offset
        with _s.socket(_s.AF_INET, _s.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    return start
