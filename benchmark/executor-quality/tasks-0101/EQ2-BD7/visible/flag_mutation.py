from __future__ import annotations

from collections.abc import Callable

from flag_state import FlagRevisionChain
from models import AuthorizationDecision, FlagMutationRequest, MutationDenied, MutationOutcome


def apply_flag_mutation(
    chain: FlagRevisionChain,
    request: FlagMutationRequest,
    authorize: Callable[[], AuthorizationDecision],
) -> MutationOutcome | MutationDenied:
    recorded = chain.recorded(request.operation_key)
    if recorded is not None:
        return recorded

    committed = chain.append(request)
    decision = authorize()
    if not decision.authorized:
        return MutationDenied(status="denied", reason=decision.reason or "token_denied")
    return committed
