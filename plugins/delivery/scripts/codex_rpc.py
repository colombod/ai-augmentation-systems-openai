"""Native Codex stdio adapter. No auth copying or approval/hook bypass."""
import json
import queue
import re
import subprocess
import threading
import time


LOCAL_TOOL_OVERRIDES = ['-c', 'features.apps=false', '-c', 'apps._default.enabled=false',
    '-c', 'computer_use.default_app_access="deny"',
    '-c', 'browser_use.default_origin_policy.access="deny"',
    '-c', 'browser_use.default_origin_policy.uploads="deny"',
    '-c', 'browser_use.default_origin_policy.downloads="deny"',
    '-c', 'browser_use.default_origin_policy.full_cdp_access="deny"']


class ProtocolError(RuntimeError):
    pass


class CodexRPC:
    def __init__(self, cwd, receive, command=None, _isolated=False):
        self.receive = receive
        self.serial = 0
        self.messages = queue.Queue()
        self.process = subprocess.Popen(command or ['codex', 'app-server', '--stdio',
            '-c', 'mcp_servers={}', '-c', 'plugins={}'] + LOCAL_TOOL_OVERRIDES,
                                        cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        text=True, bufsize=1)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        # Never inherit connected tools into a lane whose protection is local FS.
        # Table replacement can change across CLI releases: inspect effective
        # config, fail closed rather than assuming our overrides took effect.
        try:
            initialized = self.call('initialize', {'clientInfo': {'name':'delivery_coordinator','version':'0.1.0'},
                                                  'capabilities':{'experimentalApi':True}})
            self.send({'method':'initialized'})
            config = self.call('config/read', {'includeLayers': False}).get('config')
            if not isinstance(config, dict):
                raise ProtocolError('Native config/read compatibility check failed')
            enabled = [name for name, spec in (config.get('mcp_servers') or {}).items()
                       if not isinstance(spec, dict) or spec.get('enabled', True)]
            plugins = [name for name, spec in (config.get('plugins') or {}).items()
                       if not isinstance(spec, dict) or spec.get('enabled', True)]
            if enabled or plugins:
                if _isolated or command is not None:
                    raise ProtocolError('Connected tools remain enabled; cannot enforce role lanes')
                # Native config overrides merge tables. Disable each observed
                # connector by name and re-read effective configuration. Never
                # copy user config, auth, or table contents to another home.
                overrides = ['codex', 'app-server', '--stdio'] + LOCAL_TOOL_OVERRIDES
                for table, names in (('mcp_servers', enabled), ('plugins', plugins)):
                    for name in names:
                        if not re.fullmatch(r'[A-Za-z0-9_@/-]+', name):
                            raise ProtocolError('Unsupported connector config key; cannot safely disable')
                        overrides += ['-c', table+'.'+name+'.enabled=false']
                self.close()
                self.__init__(cwd, receive, command=overrides, _isolated=True)
                return
            if config.get('features', {}).get('apps') is not False or config.get('apps', {}).get('_default', {}).get('enabled') is not False:
                raise ProtocolError('Cannot verify connected-app feature is disabled')
            computer = config.get('computer_use') or {}
            browser = config.get('browser_use') or {}
            if computer.get('default_app_access') != 'deny':
                raise ProtocolError('Cannot verify native computer access is denied')
            if any(value == 'allow' for value in (computer.get('macos') or {}).get('bundle_ids', {}).values()):
                raise ProtocolError('Explicit computer app grants conflict with role isolation')
            windows = computer.get('windows') or {}
            if any(value == 'allow' for value in (windows.get('aumids') or {}).values()) or windows.get('exes'):
                raise ProtocolError('Explicit Windows computer grants require a validated deny adapter')
            required = ('access','uploads','downloads','full_cdp_access')
            if any((browser.get('default_origin_policy') or {}).get(key) != 'deny' for key in required):
                raise ProtocolError('Cannot verify native browser access is denied')
            if any(any(policy.get(key) == 'allow' for key in required) for policy in (browser.get('origins') or {}).values()):
                raise ProtocolError('Explicit browser origin grants conflict with role isolation')
            cursor = None
            server_count = 0
            seen_cursors = set()
            while True:
                listing = self.call('mcpServerStatus/list', {'cursor':cursor, 'limit':100})
                if not isinstance(listing.get('data'), list):
                    raise ProtocolError('Native tool inventory is incompatible')
                server_count += len(listing['data'])
                if any(item.get('tools') for item in listing['data']):
                    raise ProtocolError('Native inventory exposes connected tools despite isolation')
                cursor = listing.get('nextCursor')
                if not cursor:
                    break
                if cursor in seen_cursors:
                    raise ProtocolError('Native tool inventory cursor loop')
                seen_cursors.add(cursor)
            self.compatibility = {'initialize': initialized,
                'connected_tool_inventory': {'servers': server_count, 'tools':0},
                'connected_tool_policy': 'disabled; effective config checked',
                'apps_feature': False, 'native_computer_browser_policy':'deny; effective config checked'}
        except BaseException:
            self.close()
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    self.messages.put({'local_error': 'invalid_protocol_json'})
        finally:
            self.messages.put({'local_error': 'server_disconnected'})

    def send(self, message):
        try:
            self.process.stdin.write(json.dumps(message) + '\n')
            self.process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as error:
            raise ProtocolError('server_disconnected') from error

    def dispatch(self, timeout=0):
        try:
            message = self.messages.get(timeout=timeout)
        except queue.Empty:
            return False
        if 'local_error' in message:
            raise ProtocolError(message['local_error'])
        self.receive(message)
        return True

    def call(self, method, params, timeout=40):
        self.serial += 1
        serial = self.serial
        self.send({'id': serial, 'method': method, 'params': params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                message = self.messages.get(timeout=max(.01, deadline-time.monotonic()))
            except queue.Empty:
                break
            if 'local_error' in message:
                raise ProtocolError(message['local_error'])
            if message.get('id') == serial and 'method' not in message:
                if 'error' in message:
                    raise ProtocolError(str(message['error']))
                if not isinstance(message.get('result'), dict):
                    raise ProtocolError('invalid_result')
                return message['result']
            self.receive(message)
        # A timeout has unknown effects; callers must reconcile, not retry blindly.
        raise ProtocolError('rpc_timeout:' + method)

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.reader.join(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()
