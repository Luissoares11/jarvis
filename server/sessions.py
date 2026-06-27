from app.memory.context import make_context

_sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = make_context()
    return _sessions[session_id]