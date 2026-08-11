from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    authorized: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ActorToken:
    value: str
    actor_id: str
    status: str
    environments: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FlagMutationRequest:
    operation_key: str
    flag_key: str
    environment: str
    actor_id: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class FlagRevision:
    operation_key: str
    flag_key: str
    environment: str
    actor_id: str
    revision: int
    enabled: bool


@dataclass(frozen=True, slots=True)
class MutationOutcome:
    status: str
    operation_key: str
    flag_key: str
    environment: str
    revision: int
    enabled: bool


@dataclass(frozen=True, slots=True)
class MutationDenied:
    status: str
    reason: str
