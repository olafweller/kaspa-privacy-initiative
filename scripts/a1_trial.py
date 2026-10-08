#!/usr/bin/env python3
"""Small S0 trial runner. Offline by default; --live explicitly enables TN10 RPC.

C's validating node is trusted for completeness/acceptance (not a light-client
proof). Loss/pruning/reorg stops the trial. Never retries a monetary submission.
All retained files are private by default; publish only reviewed projections.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

import a1_check as c
import a1_recovery as r
from a1_fee_check import fee_requirements
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    """Exclusive durable write: an interrupted intent remains consumed."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY)
    try: os.fsync(directory)
    finally: os.close(directory)


def sompi(value):
    n = r.rpc_uint(value)
    c.require(n <= c.MAX_SOMPI, 'sompi overflow')
    return n


def native_entry(entry):
    c.keys(entry, 'amount scriptPublicKey blockDaaScore isCoinbase covenantId', 'UTXO entry')
    c.require(type(entry['isCoinbase']) is bool, 'coinbase flag required')
    return dict(entry, amount=sompi(entry['amount']), blockDaaScore=r.rpc_uint(entry['blockDaaScore']),
                scriptPublicKey=r.rpc_spk(entry['scriptPublicKey']).hex())


def inventory(items):
    entries = {}; utxos = []
    for item in items:
        p = item['outpoint']; txid = p['transactionId']; c.unhex(txid, 32)
        index = r.rpc_uint(p['index'], 32); entry = native_entry(item['entry'])
        key = txid + ':' + str(index)
        c.require(key not in entries, 'duplicate current outpoint')
        entries[key] = entry
        utxos.append({'transaction_id': txid, 'index': str(index), 'value': str(entry['amount']),
                      'spk_hex': entry['scriptPublicKey'], 'covenant': entry['covenantId']})
    return entries, utxos


def scan_history(manifest, locator, checkpoint, history, callback):
    """Reuse strict scanner; S0 trials reject any changed selected-chain prefix."""
    c.require(checkpoint['manifest_sha256'] == locator['artifact_index_sha256'], 'wrong checkpoint artifacts')
    c.require(checkpoint['hash'] == locator['scan_start_hash'] and
              checkpoint['blue_score'] == locator['scan_start_blue_score'] and
              checkpoint['daa_score'] == locator['scan_start_daa_score'], 'wrong checkpoint')
    c.require(checkpoint['instance_hex'] == manifest['instance_hex'] and
              checkpoint['genesis_hex'] == manifest['genesis_hex'], 'checkpoint identity mismatch')
    c.unhex(history['horizon'], 32)
    scanner = r.Scanner(locator, manifest, callback, checkpoint['manifest_sha256'])
    for page in history['pages']:
        c.require(not page['response']['removedChainBlockHashes'], 'reorg: stop; use a fresh trial')
        scanner.page(page, history['horizon'])
    _, utxos = inventory(history['utxos'])
    report = scanner.reconcile_utxos(utxos, history['horizon'])
    c.require(report['lineage_history_complete'], 'incomplete funding lineage')
    return report


class Trial:
    def __init__(self, config, live=False):
        self.cfg = config; self.live = live
        c.require(config['network'] == 'testnet-10', 'TN10 only')
        self.run = Path(config['run']).resolve()
        self.bundle = Path(config['bundle']).resolve()
        self.binary = str(Path(config['binary']).resolve())
        self.reference = str(Path(config['reference_binary']).resolve())

    def command(self, *args):
        env = dict(os.environ, TMPDIR=str(self.run))
        result = subprocess.run(list(map(str, args)), cwd=ROOT, env=env, check=True,
                                capture_output=True, text=True)
        return json.loads(result.stdout)

    def rpc(self, op, **values):
        # Crucially, reject before spawning a process or instantiating RpcClient.
        c.require(op == 'sdk-check' or self.live, 'network disabled: explicit --live required')
        payload = dict(op=op, network='testnet-10', sdk_dir=self.cfg['sdk_dir'], **values)
        if op != 'sdk-check': payload['rpc_url'] = self.cfg['rpc_url']
        result = subprocess.run(['node', str(ROOT/'scripts/a1_trial_rpc.mjs')],
                                input=json.dumps(payload), capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def manifest(self):
        manifest = c.load_json(self.bundle/'manifest.json')
        intent = c.load_json(Path(self.cfg['retained'])/'owner-intent.json')
        c.require(manifest['network'] == 'testnet-10' and manifest['genesis_hex'] == c.GENESIS.hex(), 'wrong genesis/network')
        c.require(intent['scope'] == 'testnet-10-test-kas', 'never fund fixture bundles')
        c.require(intent['instance_hex'] == manifest['instance_hex'], 'wrong retained owner intent')
        return manifest

    def inspect(self):
        self.manifest()
        retained = Path(self.cfg['retained'])
        checked = self.command('python3', ROOT/'scripts/a1_check.py', self.bundle,
                               '--intent', retained/'owner-intent.json', '--receipt', retained/'setup-receipt.json',
                               '--reference-binary', self.reference)
        c.require(checked['parameter_consistency'] is True, 'parameter inspection failed')
        return checked

    def new(self):
        c.require(not self.run.exists(), 'fresh run directory required')
        self.run.mkdir(parents=True, mode=0o700)
        backup = Path(self.cfg['backup']); c.require(not backup.exists(), 'fresh backup required')
        self.command('python3', ROOT/'scripts/a1_observe.py', '--repo', ROOT,
                     '--binary', self.cfg['constructor'], '--reference-binary', self.reference,
                     '--output', self.bundle, '--retained', self.cfg['retained'],
                     '--testnet-terms', self.cfg['terms'])
        backup.mkdir(mode=0o700)
        for name in ('claim-secret.bin', 'recipient-key.bin'): shutil.move(self.bundle/name, backup/name)
        manifest = self.manifest()
        save(self.run/'run.json', {'schema':'kpi-a1-s0-trial/v1', 'instance_hex':manifest['instance_hex'],
             'manifest_sha256':c.sha((self.bundle/'manifest.json').read_bytes()),
             'source_commit':manifest['pins']['kpi_source_commit'],
             'binaries_sha256':{name:c.sha(Path(self.cfg[name]).read_bytes()) for name in ('binary','reference_binary','constructor')},
             'funded':False, 'scope':'unfunded testnet instance; no readiness or privacy claim'})
        return {'created':True, 'funded':False}

    def checkpoint(self):
        self.inspect(); manifest = self.manifest()
        observed = self.rpc('checkpoint', scripts=[manifest['states']['s0']['spk_hex']])
        c.require(not observed['utxos'], 'identity already funded')
        c.unhex(observed['hash'], 32)
        record = {'hash':observed['hash'], 'blue_score':str(r.rpc_uint(observed['blue_score'])),
                  'daa_score':str(r.rpc_uint(observed['daa_score'])), 'instance_hex':manifest['instance_hex'],
                  'genesis_hex':manifest['genesis_hex'], 'manifest_sha256':c.sha((self.bundle/'manifest.json').read_bytes())}
        save(self.run/'checkpoint.json', record)
        return {'checkpoint_retained':True, 'funded':False}

    def locator(self):
        locator = c.load_json(self.run/'locator.json'); checkpoint = c.load_json(self.run/'checkpoint.json')
        c.require(locator['artifact_index_sha256'] == c.sha((self.bundle/'manifest.json').read_bytes()), 'bundle changed')
        return locator, checkpoint

    def history(self):
        manifest = self.manifest(); locator, checkpoint = self.locator()
        scripts = [manifest['states'][name]['spk_hex'] for name in ('s0','s1')] + [manifest['recipient']['spk_hex']]
        snapshot = self.rpc('snapshot', scripts=scripts); horizon = snapshot['horizon']
        c.unhex(horizon, 32); cursor = checkpoint['hash']; pages = []
        while cursor != horizon:
            response = self.rpc('page', start=cursor)
            c.require(not response['removedChainBlockHashes'], 'reorg during history fetch')
            added = response['addedChainBlockHashes']; groups = response['chainBlockAcceptedTransactions']
            c.require(added and len(groups) == len(added), 'missing/pruned history page')
            # RPC follows a moving tip; stop exactly at the initial snapshot.
            count = added.index(horizon)+1 if horizon in added else len(added)
            pages.append({'startHash':cursor, 'response':dict(response, addedChainBlockHashes=added[:count],
                          chainBlockAcceptedTransactions=groups[:count])})
            c.require(cursor != added[count-1], 'history cursor made no progress')
            cursor = added[count-1]
        self.rpc('survives', start=checkpoint['hash']); self.rpc('survives', start=horizon)
        entries, _ = inventory(snapshot['utxos'])
        # Terminal verification needs the previously authenticated S0 context.
        context = self.run/'s0-entry.json'
        if context.exists(): entries[locator['s0_txid_hex']+':'+locator['s0_index']] = native_entry(c.load_json(context))
        return {'horizon':horizon, 'pages':pages, 'utxos':snapshot['utxos'], 'entries':entries}

    def scan(self, history):
        locator, checkpoint = self.locator()
        native = r.native_callback(self.binary, self.reference, history['entries'])
        # Scanner independently recomputes v0 IDs and every Full hash already.
        # Only v1 IDs/relevant Full spends need the native reference subprocess.
        def callback(tx, context):
            if tx['version'] == 0 and context is None:
                return {'txid':tx['verboseData']['transactionId'], 'full_hash':r.full_hash(tx)}
            return native(tx, context)
        return scan_history(self.manifest(), locator, checkpoint, history,
                            callback)

    def submit_once(self, label, body, entry=None):
        c.require(self.live, 'offline submission forbidden')
        # Both A and B may attempt one competing exit, each with a distinct body.
        # A lost response/crash consumes this intent; only verify may reconcile it.
        save(self.run/(label+'-submission-intent.json'), {'txid':body['id'], 'full_hash':r.full_hash(body),
             'instance_hex':self.manifest()['instance_hex'], 'started_unix_ns':time.time_ns()})
        try:
            response = self.rpc('submit', transaction=body, **({} if entry is None else {'entry':entry}))
        except Exception:
            save(self.run/(label+'-submission-unknown.json'), {'txid':body['id'], 'outcome':'unknown-or-rejected; verify only, never retry'})
            raise
        c.require(response['transactionId'] == body['id'], 'submission response ID mismatch')
        save(self.run/(label+'-submission.json'), response)
        return response

    def fund(self):
        self.inspect(); manifest = self.manifest(); state = manifest['states']['s0']
        checkpoint = c.load_json(self.run/'checkpoint.json')
        c.require(checkpoint['manifest_sha256'] == c.sha((self.bundle/'manifest.json').read_bytes()) and
                  checkpoint['instance_hex'] == manifest['instance_hex'] and checkpoint['genesis_hex'] == manifest['genesis_hex'], 'wrong pre-funding checkpoint')
        self.rpc('survives', start=checkpoint['hash'])
        # Plan is exclusive too: no second wallet plan for the same identity.
        plan = self.rpc('fund-plan', wallet=self.cfg['wallet'], spk=state['spk_hex'], amount=str(sompi(state['R'])),
                        funding_validator=self.cfg['funding_validator'], context_file=str(self.run/'fund-context.json'),
                        body_file=str(self.run/'fund-transaction.json'))
        c.require(plan['native_full'] is True, 'funding lacks native Full')
        body = plan['transaction']; index = r.rpc_uint(plan['index'], 32)
        output = body['outputs'][index]
        c.require(sompi(output['value']) == sompi(state['R']) and output['scriptPublicKey'] == state['spk_hex'] and output['covenant'] is None, 'wrong S0 funding plan')
        locator = dict(network='testnet-10', genesis_hex=manifest['genesis_hex'], instance_hex=manifest['instance_hex'],
             s0_txid_hex=body['id'], s0_index=str(index), s0_amount=state['R'], s0_spk_hex=state['spk_hex'], s0_covenant=None,
             scan_start_hash=checkpoint['hash'], scan_start_blue_score=checkpoint['blue_score'],
             scan_start_daa_score=checkpoint['daa_score'], artifact_index_sha256=checkpoint['manifest_sha256'])
        save(self.run/'locator.json', locator)  # Intended S0 outpoint before broadcasting, never a guessed pointer.
        self.rpc('survives', start=checkpoint['hash'])
        self.submit_once('fund', body)
        while True:
            history = self.history()
            # Do not mistake an unconfirmed deposit for malformed history.
            accepted = any(tx['verboseData']['transactionId'] == body['id'] for p in history['pages']
                           for g in p['response']['chainBlockAcceptedTransactions'] for tx in g['acceptedTransactions'])
            point = locator['s0_txid_hex']+':'+locator['s0_index']
            if not accepted or point not in history['entries']:
                time.sleep(2); continue
            report = self.scan(history)
            if report['funding_body_verified']:
                save(self.run/'s0-entry.json', history['entries'][point])
                save(self.run/'fund-accepted.json', {'txid':body['id'], 'report':report})
                return {'funding_txid':body['id'], 'amount_sompi':sompi(state['R'])}
            time.sleep(2)

    def exit(self, role, history=None, prepare_only=False, submit_prepared=False, submit_at=None):
        label = role+'-exit'
        c.require(not (self.run/(label+'-submission-intent.json')).exists(), 'used exit identity: verify only')
        self.inspect(); manifest = self.manifest(); locator, _ = self.locator()
        backup = Path(self.cfg['backup'])
        self.command(self.binary, 'check-backup', self.bundle, backup/'claim-secret.bin', backup/'recipient-key.bin')
        history = self.history() if history is None else history
        report = self.scan(history)
        c.require(report['state'] == 's0' and report['lineage_history_complete'], 'S0 unavailable; no fallback exit')
        key = locator['s0_txid_hex']+':'+locator['s0_index']; entry = native_entry(history['entries'][key])
        c.require(entry['isCoinbase'] is False and entry['covenantId'] is None, 'invalid reserve context')
        request = {'txid':locator['s0_txid_hex'], 'index':locator['s0_index'], 'entry':entry}
        request_path = self.run/(label+'-request.json'); body_path = self.run/(label+'-transaction.json')
        if not submit_prepared:
            save(self.run/(label+'-history.json'), history); save(request_path, request)
            fresh = self.command(self.binary, 'fresh-terminal', self.bundle, 's0_terminal', backup/'claim-secret.bin', request_path, body_path)
            c.require(fresh['fresh_proof'] is True and fresh['native_full'] is True, 'fresh proof failed')
            body = c.load_json(body_path)
            if role == 'a':
                # Lock-disabled sequences distinguish A/B txids in a race; no output/proof change.
                body['inputs'][0]['sequence'] = str(2**64-2)
                mutation = self.run/(label+'-prepare.json'); save(mutation, {'transaction':body, 'entry':entry})
                prepared = self.command(self.binary, 'prepare-body', mutation)
                body = prepared['transaction']
                save(self.run/(label+'-race-body.json'), body)
            save(self.run/(label+'-prepared.json'), {'transaction':body, 'entry':entry})
        else:
            prepared = c.load_json(self.run/(label+'-prepared.json'))
            c.require(native_entry(prepared['entry']) == entry, 'prepared input context changed')
            body = prepared['transaction']
        self.check_terminal(body, entry, role)
        if not (self.run/'s0-entry.json').exists(): save(self.run/'s0-entry.json', entry)
        if prepare_only: return {'prepared':True, 'txid':body['id'], 'submitted':False}
        c.require(self.live and history is not None, 'offline proof only; --prepare-only required')
        if submit_at is not None:
            # Absolute deadline only synchronizes competing submissions; never
            # acts as a trial-expiry or weakens any funds/evidence check.
            while time.time() < submit_at: time.sleep(max(0, min(1, submit_at-time.time())))
        # Re-fetch after expensive proving; reorg/spent/wrong entry fails before intent.
        current = self.history(); current_report = self.scan(current)
        c.require(current_report['state'] == 's0' and native_entry(current['entries'][key]) == entry, 'stale/spent reserve before submission')
        self.submit_once(label, body, entry)
        return self.observe(body['id'])

    def check_terminal(self, body, entry, role):
        manifest = self.manifest(); locator, _ = self.locator(); branch = manifest['branches']['s0_terminal']
        c.require(len(body['inputs']) == 1 and body['inputs'][0]['previousOutpoint'] ==
                  {'transactionId':locator['s0_txid_hex'], 'index':int(locator['s0_index'])}, 'wrong exit input')
        c.require(body['inputs'][0]['sequence'] == str(2**64-(2 if role == 'a' else 1)), 'wrong race sequence')
        c.require(len(body['outputs']) == len(branch['outputs']), 'wrong exit outputs')
        for actual, expected in zip(body['outputs'], branch['outputs']):
            c.require(sompi(actual['value']) == sompi(expected['value']) and actual['scriptPublicKey'] == expected['spk_hex'] and actual['covenant'] is None, 'wrong payout')
        decoded = self.rpc('sdk-check', transaction=body, entry=entry)['transaction']
        c.require(decoded == body, 'SDK exact readback failed')
        with tempfile.TemporaryDirectory(dir=self.run) as directory:
            request = Path(directory)/'validate.json'; save(request, {'transaction':decoded, 'entry':entry})
            result = self.command(self.binary, 'validate-body', request)
        c.require(result['full_valid'] is True and result['txid'] == body['id'] and result['full_hash'] == r.full_hash(body) and
                  sompi(result['fee']) == sompi(branch['fee']), 'native Full/body/fee mismatch')
        _, _, _, minimum = fee_requirements(result['native_masses'], Fraction(100))
        c.require(sompi(branch['fee']) >= minimum, 'fixed exit fee below pinned relay requirement')
        return result

    def observe(self, expected=None):
        first = None; accepting = None
        while True:
            history = self.history(); report = self.scan(history)
            if report['state'] == 'terminal':
                c.require(len(report['transitions']) == 1 and report['transitions'][0]['branch'] == 's0_terminal', 'unexpected successor/duplicate payout')
                txid = report['transitions'][0]['txid']
                c.require(expected is None or txid == expected, 'different race winner; verify public result')
                bodies = [tx for p in history['pages'] for g in p['response']['chainBlockAcceptedTransactions'] for tx in g['acceptedTransactions']
                          if tx['verboseData']['transactionId'] == txid]
                hashes = {r.full_hash(tx) for tx in bodies}; c.require(len(hashes) == 1, 'ambiguous accepted body')
                winner = (txid, next(iter(hashes)))
                matching = [x for x in history['utxos'] if x['outpoint']['transactionId'] == txid and r.rpc_uint(x['outpoint']['index'],32) == 0]
                want = self.manifest()['branches']['s0_terminal']['outputs'][0]
                c.require(len(matching) == 1 and sompi(matching[0]['entry']['amount']) == sompi(want['value']) and
                          r.rpc_spk(matching[0]['entry']['scriptPublicKey']).hex() == want['spk_hex'] and matching[0]['entry']['covenantId'] is None, 'missing/wrong payout UTXO')
                if first is None: first = time.monotonic(); accepting = winner
                c.require(winner == accepting, 'accepted payout changed during observation')
                elapsed = time.monotonic()-first
                if elapsed >= 120:
                    outcome = {'schema':'kpi-a1-s0-result/v1', 'network':'testnet-10', 'txid':txid, 'full_hash':winner[1],
                               'payout_sompi':sompi(want['value']), 'fee_sompi':sompi(report['fees']),
                               'recipient':self.manifest()['recipient']['address'], 'observed_seconds':elapsed,
                               'reserve_spent':True, 'single_accepted_terminal':True, 'history':history}
                    save(self.run/('result-'+str(time.time_ns())+'.json'), outcome)
                    return {k:v for k,v in outcome.items() if k != 'history'}
            elif first is not None: raise c.Invalid('accepted payout disappeared')
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--live', action='store_true', help='enable TN10 RPC; requires separately authorized phase B')
    roles = parser.add_subparsers(dest='role', required=True)
    a = roles.add_parser('a').add_subparsers(dest='action', required=True)
    a.add_parser('new'); a.add_parser('fund'); exits = [a.add_parser('exit-s0')]
    roles.add_parser('c').add_subparsers(dest='action', required=True).add_parser('checkpoint')
    exits.append(roles.add_parser('b').add_subparsers(dest='action', required=True).add_parser('recover'))
    for exit_parser in exits:
        exit_parser.add_argument('--history', type=Path, help='offline retained/synthetic history')
        group = exit_parser.add_mutually_exclusive_group()
        group.add_argument('--prepare-only', action='store_true'); group.add_argument('--submit-prepared', action='store_true')
        exit_parser.add_argument('--submit-at', type=float, help='race broadcast Unix time; prepare both bodies first')
    verify = roles.add_parser('verify'); verify.add_argument('--history', type=Path)
    args = parser.parse_args(); os.umask(0o077)
    c.require(args.config.stat().st_mode & 0o777 == 0o600, 'config must be private mode 0600')
    trial = Trial(c.load_json(args.config), args.live)
    tempfile.tempdir = str(trial.run)
    if args.role == 'verify':
        trial.inspect()
        result = trial.scan(c.load_json(args.history)) if args.history else trial.observe()
    elif args.action == 'new': result = trial.new()
    elif args.action == 'checkpoint': result = trial.checkpoint()
    elif args.action == 'fund': result = trial.fund()
    else:
        c.require(not args.history or args.prepare_only, 'retained history can only prepare offline, never submit')
        result = trial.exit(args.role, c.load_json(args.history) if args.history else None,
                            args.prepare_only, args.submit_prepared, args.submit_at)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try: main()
    except (c.Invalid, OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise SystemExit('A1 step failed safely; inspect local evidence. No automatic retry or submission.')
