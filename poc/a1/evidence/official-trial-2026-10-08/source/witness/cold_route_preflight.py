"""Actual pinned existing route validation; local only, before future prefix.

This validates binding/credential files without SSH or creating E/live state.
It is one cold-bootstrap prerequisite, not a runtime qualification receipt.
"""
import argparse, hashlib, importlib.util, json, os, pathlib, re, sys

def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def check(helper_root, helper_pin, binding, cfg):
    root = pathlib.Path(helper_root).absolute()
    require(not root.is_symlink(), 'helper root symlink')
    helper = root/'controller_access.py'
    require(sha(helper) == helper_pin, 'actual controller_access pin')
    run = binding['standby_run_id']
    require(re.fullmatch(r'[a-z0-9][a-z0-9-]{7,119}', run) is not None, 'run syntax')
    require('d4643a60ec064d6b92316d2bc872c411' not in json.dumps(binding), 'consumed BASE')
    require(cfg['run_id'] == run and binding['C']['config'] == cfg,
            'new standby config/run binding')
    require(cfg['planned_live_run_id'] == binding['planned_live_run_id'],
            'future live identity/config binding')
    for flag in ['execution_authorized', 'terminal_execution_authorized',
                 'funding_authorized', 'poweroff_authorized']:
        require(cfg.get(flag) is False, 'cold route has live authority')
    route = binding['A_controller_route']
    parent = pathlib.Path(binding['A_credential_root'])
    require(parent.is_absolute() and parent.is_dir() and not parent.is_symlink(),
            'existing actual credential parent')
    require(route['host_key_alias'] == 'tn10-finite-' + run, 'new HostKeyAlias')
    for field in ['key', 'known_hosts']:
        p = pathlib.Path(route[field])
        require(p.parent == parent and not p.is_symlink(), 'same credential parent')
        require(p.stat().st_uid == os.getuid(), 'actual credential owner')
        require(sha(p) == route[field+'_sha256'], 'actual credential pin')
    rows = pathlib.Path(route['known_hosts']).read_text().splitlines()
    require(len(rows) == 1 and len(rows[0].split()) == 3 and
            rows[0].split()[0] == route['host_key_alias'], 'exact known-host row/alias')
    # Existing validator checks private-key 0600, target, forced command/config
    # pin and immutable same-parent credentials. Never duplicate its argv logic.
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location('cold_actual_controller_access', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(pathlib.Path(module.__file__).resolve() == helper.resolve(), 'actual module origin')
    argv = module.route(binding)
    transport, request = module.transport_for(cfg, binding, 'finite-checkpoint', None)
    require(transport == argv and json.loads(request) == {'action': 'checkpoint'},
            'actual transport/route agreement')
    sockets = [binding['C']['socket_root']+'/control.sock']
    channel = module.worker_channel(binding['planned_live_run_id'])
    sockets.append(channel['intent_socket'])
    for name in sockets:
        require('\0' not in name and 0 < len(name.encode('utf-8')) <= 107,
                'socket UTF-8 path exceeds 107 bytes')
    return {'passed': True, 'actual_route_and_transport_for': True,
            'no_SSH_invoked': True, 'no_prefix_or_capture_started': True,
            'standby_run_id': run, 'controller_access_sha256': helper_pin,
            'socket_lengths_utf8': [len(x.encode('utf-8')) for x in sockets],
            'funding_authorized': False, 'runtime_qualified': False}

def main():
    p = argparse.ArgumentParser()
    for arg in ['helper-root', 'helper-sha256', 'binding', 'binding-sha256',
                'config', 'config-sha256']:
        p.add_argument('--'+arg, required=True)
    a = p.parse_args()
    require(sha(a.binding) == a.binding_sha256, 'binding pin')
    require(sha(a.config) == a.config_sha256, 'config pin')
    print(json.dumps(check(a.helper_root, a.helper_sha256,
                           json.loads(pathlib.Path(a.binding).read_bytes()),
                           json.loads(pathlib.Path(a.config).read_bytes()))))

if __name__ == '__main__':
    main()
