#!/usr/bin/env python3
"""Offline user-owned wallet onboarding. No network, provider or broadcast client."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
WALLET_SHA = 'aeb84c7a3edd9b076e28c3035729fca9df0d582e44d33cbc951d697fb33c3c90'
PARAMETERS_SHA = '812b3bda0ec5f9b0c17fc1d530e49fc21defc9dcc5ea9c70a133ca62fec31e99'
RECEIVE_FIELDS = {'schema', 'domain', 'owner', 'incoming'}
ROLES = ('alice', 'bob')


def checked_package():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise ValueError('Dit pakket vereist Linux x86_64, bijvoorbeeld Ubuntu 24.04 onder WSL2.')
    manifest = json.loads((HERE/'package.json').read_text())
    if manifest['schema'] != 'KPI_LOCAL_RECOVERY_START_KIT_V1' or manifest['walletSha256'] != WALLET_SHA or manifest['publicParametersSha256'] != PARAMETERS_SHA:
        raise ValueError('Onverwachte pakketversie.')
    for name, record in manifest['files'].items():
        p = HERE/name
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(HERE):
            raise ValueError('Ongeldig pakketbestand: '+name)
        raw = p.read_bytes()
        if len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('Pakketcontrole mislukt: '+name)
    binary = HERE/'bin/kpi-recovery-native-wallet'
    if hashlib.sha256(binary.read_bytes()).hexdigest() != WALLET_SHA:
        raise ValueError('Onverwachte walletsoftware.')
    binary.chmod(0o755)  # ZIP extractors may discard executable permissions; only after hash verification.
    return binary


def call(binary, *args, success=True):
    # No injected provider/network/remote-administration credentials enter wallet children.
    env = {k:os.environ[k] for k in ('PATH','HOME','LANG','TZ') if k in os.environ}
    env['RAYON_NUM_THREADS'] = '4'
    r = subprocess.run([str(binary), *map(str,args)], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, env=env, timeout=120)
    if (r.returncode == 0) != success:
        raise RuntimeError('Lokale walletcontrole mislukt: '+r.stderr.strip()[:400])
    return r


def receive(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
        raise ValueError('Ongeldige openbare ontvanggegevens.')
    r = json.loads(path.read_text())
    if set(r) != RECEIVE_FIELDS or r['schema'] != 'KPI_USER_RECEIVE_V1':
        raise ValueError('Ontvanggegevens bevatten onverwachte velden.')
    for name in ('domain','owner','incoming'):
        if not isinstance(r[name],str) or len(r[name]) != 64 or bytes.fromhex(r[name]).hex() != r[name]:
            raise ValueError('Ongeldige ontvanggegevens: '+name)
    return r


def doctor(binary):
    with tempfile.TemporaryDirectory(prefix='kpi-wallet-doctor-') as tmp:
        root = Path(tmp)
        own = root/'temporary-test-wallet'
        call(binary, 'init', own)
        receive(own/'receive.json')
        for name in ('wallet.backup','native.key'):
            if stat.S_IMODE((own/name).stat().st_mode) != 0o600:
                raise ValueError('Het bestandssysteem handhaaft de vereiste private bestandsrechten niet.')
        targets = json.loads((HERE/'fixtures/targets.json').read_text())['batches']
        cases = ('deposit','credit-transfer','bob-exit','bob-reconcile','alice-exit','alice-reconcile')
        start = targets[cases[0]]['expectedJournalHex'][:64]
        end = targets[cases[-1]]['expectedJournalHex'][128:192]
        restored = root/'restored.state.bin'
        call(binary, 'rebuild', start, end, restored, *(HERE/'fixtures'/(c+'.input.bin') for c in cases))
        balance = json.loads(call(binary, 'scan', restored, end, own).stdout)
        if balance['spendableSompi'] != 0:
            raise ValueError('De tijdelijke testwallet hoort geen fixturetegoed te bezitten.')
        call(binary, 'scan', restored, '00'*32, own, success=False)
    print('OK: pakket, walletprogramma, private bestandsrechten en offline herstelcontrole geslaagd.')
    print('Dit gebruikte een tijdelijke testwallet. Er zijn geen persoonlijke wallets, GPU-jobs of transacties gestart.')


def init(binary, location):
    location = location.expanduser().resolve()
    # WSL's Linux home preserves Unix permissions; Windows-mounted/synced paths do not establish that boundary.
    if str(location).startswith(('/mnt/','/media/')):
        raise ValueError('Gebruik een map in je Linux-home, bijvoorbeeld ~/kpi-testwallets, buiten Windows-/USB-mounts.')
    if not location.parent.is_dir() or location.parent.is_symlink():
        raise ValueError('Kies een bestaande lokale bovenliggende map.')
    location.mkdir(mode=0o700)  # A fresh directory only; never overwrite a wallet.
    os.chmod(location,0o700)
    try:
        for role in ROLES:
            call(binary, 'init', location/role)
            receive(location/role/'receive.json')
        public = location/'public'
        public.mkdir(mode=0o700)
        for role in ROLES:
            data = receive(location/role/'receive.json')
            with (public/(role+'-receive.json')).open('x') as f:
                json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    except Exception:
        print('De aanmaak is onvolledig; eventueel aangemaakte sleutels zijn behouden. Overschrijf deze map niet.',file=sys.stderr)
        raise
    print('Alice en Bob zijn lokaal aangemaakt in: '+str(location))
    print('Bewaar per gebruiker wallet.backup en native.key uitsluitend op eigen media; ze zijn niet versleuteld.')
    print('Alleen de twee bestanden in deze openbare map mogen worden gedeeld: '+str(public))
    print('Dit maakt twee logische testgebruikers op jouw computer; het bewijst geen onafhankelijk beheer door twee personen.')


def public(location):
    location = location.expanduser().resolve()
    # Intentionally read only the public address files, never backup/key contents.
    for role in ROLES:
        data = receive(location/role/'receive.json')
        print(role+': '+json.dumps(data,sort_keys=True))


def main():
    p = argparse.ArgumentParser(description='Lokale voorbereiding voor de KPI TN10-herstelproef; geen netwerk of transacties.')
    sub = p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    for name in ('init','public'):
        c = sub.add_parser(name);c.add_argument('directory',type=Path)
    a = p.parse_args()
    binary = checked_package()
    if a.command == 'doctor':doctor(binary)
    elif a.command == 'init':init(binary,a.directory)
    else:public(a.directory)


if __name__ == '__main__':
    try:main()
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as e:
        print('STOP: '+str(e),file=sys.stderr);raise SystemExit(1)
