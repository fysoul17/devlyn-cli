from dataclasses import dataclass

@dataclass(frozen=True)
class Job:
    job_id: str
    payload: object
    state: str
    available_at: float
    attempts: int
    owner: str | None
    token: str | None
    lease_until: float | None
    last_error: str | None

@dataclass(frozen=True)
class Receipt:
    job_id: str
    payload: object
    owner: str
    token: str
    lease_until: float
    attempt: int

@dataclass(frozen=True)
class ProcessResult:
    state: str
    job_id: str | None = None
