"""Local prototype for trusted hosts; no transport or host sandbox.

Only trusted callbacks may access the sink. A real adapter must atomically enforce
destination, authority and policy revisions. Tickets are instance-local and non-durable.
Shell, HTTP, connector, upload and delegated calls are not intercepted.
"""
from dataclasses import dataclass
import math
import re
import threading
import time


class Blocked(ValueError):
    """A pre-dispatch check did not establish permission."""


@dataclass(frozen=True)
class Destination:
    """Coherent verified binding; revision values must never be reused after change."""
    identity: str
    owner: str
    audience: str
    visibility: str
    revision: str
    authority_revision: str
    policy_revision: str


@dataclass(frozen=True)
class Receipt:
    status: str


@dataclass(frozen=True)
class _Grant:
    payload: bytes
    operation: str
    destination: Destination
    issued: float
    expires: float


class Publisher:
    """Fail-closed dispatch within one trusted process.

    verify(operation, destination_id) returns a coherent trusted binding.
    authorize/classify(payload, operation, destination) must evaluate that bound
    snapshot and return exactly True. A changed permission or policy MUST advance
    its revision, even when the destination itself is unchanged.
    send(payload, operation, destination) must atomically compare ALL binding
    fields with current destination/authority/policy state at the point of effect,
    and return exactly True only for confirmed completion. Separate prechecks
    followed by an unconditional send do not implement this adapter contract.
    Callbacks, the clock and this process are trusted, not candidate-controlled.
    Unknown completion quarantines the instance; automatic retry is unsupported.
    """

    def __init__(self, *, routes, verify, authorize, classify, send, clock=time.monotonic,
                 ttl=30, max_bytes=1_048_576):
        if type(routes) is not frozenset or not routes or len(routes) > 64:
            raise ValueError('A bounded trusted route registry is required')
        for route in routes:
            if type(route) is not tuple or len(route) != 2 or any(
                    type(v) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', v)
                    for v in route):
                raise ValueError('Routes require fixed operation and destination identifiers')
        if any(not callable(f) for f in (verify, authorize, classify, send, clock)):
            raise ValueError('Trusted callbacks required')
        if type(ttl) not in (int, float) or not math.isfinite(ttl) or not 0 < ttl <= 300:
            raise ValueError('Finite ticket lifetime required')
        if type(max_bytes) is not int or not 0 < max_bytes <= 1_048_576:
            raise ValueError('Invalid payload limit')
        self._verify, self._authorize, self._classify, self._send = verify, authorize, classify, send
        self._clock, self._ttl, self._max_bytes = clock, ttl, max_bytes
        self._routes = routes
        self._lock = threading.Lock()
        self._grants = {}
        self._unknown = False

    def _now(self):
        now = self._clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            raise Blocked()
        return now

    def _check(self, payload, operation, destination_id):
        if self._unknown or type(payload) is not bytes or not 0 < len(payload) <= self._max_bytes:
            raise Blocked()
        if any(type(v) is not str or not v.strip() or len(v) > 512
               for v in (operation, destination_id)):
            raise Blocked()
        # Resolve only fixed host-supplied routes. Untrusted identifiers never
        # reach a callback that might perform external verification.
        if (operation, destination_id) not in self._routes:
            raise Blocked()
        dest = self._verify(operation, destination_id)
        if type(dest) is not Destination or any(type(v) is not str or not v.strip()
                or len(v) > 512 for v in (dest.identity, dest.owner, dest.audience,
                                         dest.visibility, dest.revision,
                                         dest.authority_revision, dest.policy_revision)):
            raise Blocked()
        if dest.identity != destination_id or dest.visibility not in ('public', 'private'):
            raise Blocked()
        if self._authorize(payload, operation, dest) is not True:
            raise Blocked()
        if self._classify(payload, operation, dest) is not True:
            raise Blocked()
        return dest

    def prepare(self, payload, operation, destination_id):
        """Return an opaque capability for these exact bytes, or a safe error."""
        with self._lock:
            try:
                start = self._now()
                self._grants = {t:g for t,g in self._grants.items()
                                if g.issued <= start < g.expires}
                if len(self._grants) >= 64:
                    raise Blocked()
                dest = self._check(payload, operation, destination_id)
                finish = self._now()
                if not start <= finish < start + self._ttl:
                    raise Blocked()
                ticket = object()
                self._grants[ticket] = _Grant(payload, operation, dest, start, start + self._ttl)
                return ticket
            except Exception:
                raise Blocked('Publication blocked') from None

    def dispatch(self, ticket, payload, operation, destination_id):
        """Consume once; uncertainty after entering send prevents reuse."""
        with self._lock:
            try:
                grant = self._grants.pop(ticket, None)
                if grant is None or type(payload) is not bytes or payload != grant.payload \
                        or operation != grant.operation or destination_id != grant.destination.identity:
                    return Receipt('blocked')
                now = self._now()
                if not grant.issued <= now < grant.expires:
                    return Receipt('blocked')
                dest = self._check(payload, operation, destination_id)
                if dest != grant.destination:
                    return Receipt('blocked')
                now = self._now()
                if not grant.issued <= now < grant.expires:
                    return Receipt('blocked')
            except Exception:
                return Receipt('blocked')
            # Mark uncertainty before any possible effect, including interruption.
            self._unknown = True
            try:
                confirmed = self._send(grant.payload, grant.operation, grant.destination)
            except Exception:
                return Receipt('unknown')
            if confirmed is not True:
                return Receipt('unknown')
            self._unknown = False
            return Receipt('completed')
