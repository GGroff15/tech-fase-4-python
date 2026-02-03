import time


class Session:
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.created_at = time.time()
        self.closed_at: float | None = None

    def close(self):
        self.closed_at = time.time()


class SessionRegistry:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self, correlation_id: str) -> Session:
        session = Session(correlation_id)
        self._sessions[correlation_id] = session
        return session

    def get(self, correlation_id: str) -> Session | None:
        return self._sessions.get(correlation_id)

    def close(self, correlation_id: str):
        session = self._sessions.pop(correlation_id, None)
        if session:
            session.close()

    def all(self):
        return list(self._sessions.values())
