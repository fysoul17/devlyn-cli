#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys


sys.dont_write_bytecode = True
workdir = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(workdir))

from actor_token import ActorTokenGateway
from flag_state import FlagRevisionChain
from models import ActorToken, FlagMutationRequest, MutationDenied


def setup() -> tuple[FlagRevisionChain, ActorTokenGateway]:
    chain = FlagRevisionChain([("density-control", "canary", False)])
    gateway = ActorTokenGateway(
        chain,
        [
            ActorToken("credential-alpha", "maintainer-31", "active", ("canary",)),
            ActorToken("credential-beta", "maintainer-31", "active", ("canary",)),
            ActorToken("credential-stale", "maintainer-31", "expired", ("canary",)),
            ActorToken("credential-sandbox", "maintainer-31", "active", ("sandbox",)),
        ],
    )
    return chain, gateway


def request(operation_key: str) -> FlagMutationRequest:
    return FlagMutationRequest(
        operation_key=operation_key,
        flag_key="density-control",
        environment="canary",
        actor_id="maintainer-31",
        enabled=True,
    )


def active_repeat_has_one_revision() -> bool:
    _, gateway = setup()
    change = request("repeat-operation-31")
    first = gateway.mutate_flag(change, "credential-alpha")
    second = gateway.mutate_flag(change, "credential-alpha")
    return first == second and first.status == "changed" and len(gateway.state["revisions"]) == 1


def active_rotation_reconstructs_revision() -> bool:
    _, gateway = setup()
    change = request("rotated-operation-31")
    first = gateway.mutate_flag(change, "credential-alpha")
    second = gateway.mutate_flag(change, "credential-beta")
    return first == second and first.revision == 1 and len(gateway.state["revisions"]) == 1


def expired_fresh_operation_leaves_chain_empty() -> bool:
    _, gateway = setup()
    before = gateway.state
    denied = gateway.mutate_flag(request("expired-operation-31"), "credential-stale")
    return isinstance(denied, MutationDenied) and gateway.state == before


def wrong_environment_leaves_chain_empty() -> bool:
    _, gateway = setup()
    before = gateway.state
    denied = gateway.mutate_flag(request("scope-operation-31"), "credential-sandbox")
    return isinstance(denied, MutationDenied) and gateway.state == before


def stale_retry_cannot_observe_committed_revision() -> bool:
    _, gateway = setup()
    change = request("composed-operation-31")
    committed = gateway.mutate_flag(change, "credential-alpha")
    before_stale = gateway.state
    denied = gateway.mutate_flag(change, "credential-stale")
    after_stale = gateway.state
    replayed = gateway.mutate_flag(change, "credential-beta")
    return (
        committed.status == "changed"
        and isinstance(denied, MutationDenied)
        and denied != committed
        and after_stale == before_stale
        and replayed == committed
        and len(gateway.state["revisions"]) == 1
    )


invariant = (
    "Authorized flag-change operations sharing an operation key must append one revision and replay "
    "that revision across active actor-token rotations, every token must be validated against its "
    "current actor and environment grant before the flag's revision chain is inspected or extended, "
    "and an expired or out-of-scope token repeating either a fresh or recorded operation must be denied "
    "without revealing a prior result or recording an operation marker."
)
checks = [
    active_repeat_has_one_revision(),
    active_rotation_reconstructs_revision(),
    expired_fresh_operation_leaves_chain_empty(),
    wrong_environment_leaves_chain_empty(),
    stale_retry_cannot_observe_committed_revision(),
]
identifiers = ["axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"]
print(
    json.dumps(
        {
            "manifestations": [
                {"id": identifier, "invariant": invariant, "passed": passed}
                for identifier, passed in zip(identifiers, checks, strict=True)
            ]
        },
        separators=(",", ":"),
    )
)
