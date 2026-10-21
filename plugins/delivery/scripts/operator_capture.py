"""One-shot receipts from an explicit operator-owned terminal capture channel.

The signing capability lives only inside the coordinator process. Workers receive
neither a signer tool nor a signing key. Receipts attest this client/channel and
exact request, not a person's external identity. Native permissions still apply.
"""
import copy
import hashlib
import hmac
import json
import io
import math
import os
import secrets
import threading
import time


class CaptureError(ValueError):
    pass


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                          allow_nan=False).encode('utf-8')
    except (ValueError, TypeError) as error:
        raise CaptureError('Binding must be finite JSON data') from error


def question_digest(question):
    return hashlib.sha256(canonical(question)).hexdigest()


def validate_binding(binding):
    required = {'request_id', 'native_request_id', 'thread_id', 'turn_id', 'method',
                'item_id', 'question_digest', 'source_revision', 'scope', 'question'}
    if not isinstance(binding, dict) or set(binding) != required:
        raise CaptureError('Exact native request binding is required')
    for field in ('request_id', 'thread_id', 'turn_id', 'method'):
        if not isinstance(binding[field], str) or not binding[field]:
            raise CaptureError('Missing request/thread/turn/method binding')
    if not isinstance(binding['scope'], dict) or not isinstance(binding['question'], dict):
        raise CaptureError('Question and scope must be structured objects')
    if binding['question_digest'] != question_digest(binding['question']):
        raise CaptureError('Question digest does not match the displayed request')
    canonical(binding)


def _native_response(binding, line):
    method = binding['method']
    if method in ('item/commandExecution/requestApproval', 'item/fileChange/requestApproval', 'delivery/gateAcceptance'):
        decision = line.strip().lower()
        if decision not in ('accept', 'decline', 'cancel'):
            raise CaptureError('Choose exactly accept, decline or cancel; no session-wide grant')
        return {'decision': decision}
    if method == 'item/tool/requestUserInput':
        try:
            answer = json.loads(line)
        except ValueError as error:
            raise CaptureError('User-input response must be an explicit JSON object') from error
        questions = binding['question'].get('questions')
        if not isinstance(questions, list) or not questions:
            raise CaptureError('No bound questions')
        ids = [q.get('id') for q in questions if isinstance(q, dict)]
        if len(ids) != len(questions) or len(set(ids)) != len(ids) or not all(isinstance(i, str) and i for i in ids):
            raise CaptureError('Invalid bound question identifiers')
        if not isinstance(answer, dict) or set(answer) != {'answers'} or not isinstance(answer['answers'], dict):
            raise CaptureError('Expected only an answers object')
        if set(answer['answers']) != set(ids):
            raise CaptureError('Every exact question needs an explicit response')
        for row in answer['answers'].values():
            if (not isinstance(row, dict) or set(row) != {'answers'} or
                    not isinstance(row['answers'], list) or not row['answers'] or
                    not all(isinstance(x, str) and x.strip() for x in row['answers'])):
                raise CaptureError('Empty, default or malformed answers are not consent')
        return answer
    raise CaptureError('This request type has no trusted terminal capture adapter')


class CaptureAuthority:
    def __init__(self):
        self._key = secrets.token_bytes(32)
        self._epoch = secrets.token_hex(16)
        self._requests = {}
        self._lock = threading.Lock()

    def challenge(self, binding, ttl_seconds=300):
        validate_binding(binding)
        if (not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool) or
                not math.isfinite(ttl_seconds) or ttl_seconds <= 0 or ttl_seconds > 300):
            raise CaptureError('Capture lifetime must be positive and at most five minutes')
        issued = time.time()
        value = {'nonce': secrets.token_hex(32), 'epoch': self._epoch,
                 'binding': copy.deepcopy(binding), 'issued_at': issued,
                 'expires_at': issued + ttl_seconds}
        with self._lock:
            for nonce,row in list(self._requests.items()):
                if row['challenge']['expires_at'] <= issued:
                    self._requests.pop(nonce,None)
            self._requests[value['nonce']] = {'challenge': value, 'state': 'pending'}
        return copy.deepcopy(value)

    def _pending(self, challenge, states=('pending',)):
        if not isinstance(challenge, dict):
            raise CaptureError('Unknown capture challenge')
        row = self._requests.get(challenge.get('nonce'))
        if not row or row['state'] not in states or row['challenge'] != challenge:
            raise CaptureError('Unknown, changed, consumed or revoked capture')
        if time.time() >= challenge['expires_at']:
            self._requests.pop(challenge['nonce'],None)
            raise CaptureError('Operator request expired; no default answer')
        return row

    def capture_from_terminal(self, challenge, *, terminal=None):
        """Only trusted client code invokes this; never expose it as a worker tool.

        `terminal` supports an operator-owned existing TTY (and PTY integration
        tests). It must be a real OS terminal, not an object claiming isatty().
        """
        with self._lock:
            self._pending(challenge)
        owned = terminal is None
        try:
            if owned:
                terminal = io.TextIOWrapper(io.FileIO('/dev/tty', 'r+'), encoding='utf-8',
                                            write_through=True, line_buffering=True)
            if not os.isatty(terminal.fileno()):
                raise CaptureError('Operator capture requires an actual terminal')
            binding = challenge['binding']
            terminal.write('\nDELIVERY OPERATOR REQUEST\n')
            terminal.write(json.dumps(binding, ensure_ascii=False, indent=2)+'\n')
            terminal.write('Response (accept/decline/cancel for approvals; exact answers JSON for questions): ')
            terminal.flush()
            line = terminal.readline(16385)
            if not line or len(line) > 16384:
                raise CaptureError('No complete explicit operator response')
            response = _native_response(binding, line)
            with self._lock:
                row = self._pending(challenge)
                receipt = {'challenge': copy.deepcopy(challenge), 'response': response,
                           'channel': 'operator-terminal', 'captured_at': time.time()}
                receipt['signature'] = hmac.new(self._key, canonical(receipt), hashlib.sha256).hexdigest()
                row['state'] = 'captured'
                return receipt
        except (OSError, AttributeError, ValueError) as error:
            # Failure leaves no usable response. No retry can select a default.
            self.revoke(challenge.get('nonce') if isinstance(challenge, dict) else None)
            if isinstance(error, CaptureError):
                raise
            raise CaptureError('Operator terminal capture unavailable') from error
        finally:
            if owned and terminal is not None:
                terminal.close()

    def verify_receipt(self, receipt, binding):
        validate_binding(binding)
        if not isinstance(receipt, dict) or set(receipt) != {'challenge', 'response', 'channel', 'captured_at', 'signature'}:
            raise CaptureError('An operator-client receipt is required, not answer JSON')
        unsigned = {key: value for key, value in receipt.items() if key != 'signature'}
        signature = hmac.new(self._key, canonical(unsigned), hashlib.sha256).hexdigest()
        if not isinstance(receipt['signature'], str) or not hmac.compare_digest(signature, receipt['signature']):
            raise CaptureError('Capture signature invalid')
        challenge = receipt['challenge']
        with self._lock:
            row = self._pending(challenge, states=('captured',))
            if challenge['binding'] != binding or receipt['channel'] != 'operator-terminal':
                raise CaptureError('Operator receipt does not match this exact request/source/scope')
            response = _native_response(binding, receipt['response']['decision'] if
                                        binding['method'] != 'item/tool/requestUserInput' else json.dumps(receipt['response']))
            self._requests.pop(challenge['nonce'],None)
            return copy.deepcopy(response)

    def revoke(self, nonce):
        with self._lock:
            self._requests.pop(nonce,None)

    def revoke_all(self):
        with self._lock:
            self._requests.clear()
