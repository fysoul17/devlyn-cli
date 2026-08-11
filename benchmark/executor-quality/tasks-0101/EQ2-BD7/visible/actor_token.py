from __future__ import annotations

from collections.abc import Iterable

from flag_mutation import apply_flag_mutation
from flag_state import FlagRevisionChain
from models import (
    ActorToken,
    AuthorizationDecision,
    FlagMutationRequest,
    MutationDenied,
    MutationOutcome,
)


class ActorTokenGateway:
    def __init__(self, chain: FlagRevisionChain, tokens: Iterable[ActorToken]) -> None:
        self._chain = chain
        self._tokens = {token.value: token for token in tokens}

    def authorize(self, token_value: str, request: FlagMutationRequest) -> AuthorizationDecision:
        token = self._tokens.get(token_value)
        if token is None:
            return AuthorizationDecision(False, "token_missing")
        if token.status != "active":
            return AuthorizationDecision(False, f"token_{token.status}")
        if token.actor_id != request.actor_id:
            return AuthorizationDecision(False, "token_actor_mismatch")
        if request.environment not in token.environments:
            return AuthorizationDecision(False, "token_environment_denied")
        return AuthorizationDecision(True)

    def mutate_flag(
        self, request: FlagMutationRequest, token_value: str
    ) -> MutationOutcome | MutationDenied:
        return apply_flag_mutation(
            self._chain,
            request,
            lambda: self.authorize(token_value, request),
        )

    @property
    def state(self) -> dict[str, object]:
        return self._chain.snapshot()
