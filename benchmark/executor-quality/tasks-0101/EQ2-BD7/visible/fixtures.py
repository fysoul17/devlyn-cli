from actor_token import ActorTokenGateway
from flag_state import FlagRevisionChain
from models import ActorToken, FlagMutationRequest


def flag_fixture() -> tuple[FlagRevisionChain, ActorTokenGateway]:
    chain = FlagRevisionChain(
        [
            ("checkout-redesign", "staging", False),
            ("invoice-preview", "production", False),
        ]
    )
    gateway = ActorTokenGateway(
        chain,
        [
            ActorToken("token-old", "operator-7", "expired", ("staging",)),
            ActorToken("token-current", "operator-7", "active", ("staging",)),
            ActorToken("token-rotated", "operator-7", "active", ("staging",)),
            ActorToken("token-production", "operator-7", "active", ("production",)),
            ActorToken("token-outsider", "operator-9", "active", ("staging",)),
        ],
    )
    return chain, gateway


def mutation_request(
    *,
    operation_key: str = "change-checkout-7",
    flag_key: str = "checkout-redesign",
    environment: str = "staging",
    actor_id: str = "operator-7",
    enabled: bool = True,
) -> FlagMutationRequest:
    return FlagMutationRequest(
        operation_key=operation_key,
        flag_key=flag_key,
        environment=environment,
        actor_id=actor_id,
        enabled=enabled,
    )
