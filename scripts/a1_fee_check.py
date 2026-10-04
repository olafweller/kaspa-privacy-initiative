#!/usr/bin/env python3
"""Exact rational, unfunded A1 fee/budget/resource qualification.

Quotes are read-only observations, not server-config attestations or admission.
Checks never edit terms. A failed unfunded instance must be rebuilt; a funded
failure is a liveness failure. No fee bump, sponsor or principal haircut.
"""
import argparse
import copy
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import time
import subprocess
import tempfile

import a1_recovery as recovery

import a1_check as c


def ceiling(value):
    return (value.numerator + value.denominator - 1) // value.denominator


def quote_json(path):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result: raise c.Invalid('duplicate quote field')
            result[k] = v
        return result
    return json.loads(Path(path).read_text(), parse_float=Decimal, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(c.Invalid('nonfinite quote')))


def fee_requirements(masses, chosen_rate, relay_per_kg=100000):
    """Frozen TN10 policy: overall M for headroom, non-storage N for relay.

    Native TN10 cofactors are storage=1 and transient=1/2. Use integer
    normalization, not binary-float rounding. This is source-default relay
    policy; the actual target's configuration still requires qualification.
    """
    c.require(set(masses) == {'compute', 'storage', 'transient'} and
              all(type(n) is int and n >= 0 for n in masses.values()), 'native mass integers')
    c.require(type(relay_per_kg) is int and relay_per_kg > 0, 'relay minimum')
    c.require(isinstance(chosen_rate, Fraction) and chosen_rate >= Fraction(relay_per_kg, 1000), 'rate covers relay minimum')
    normalized_transient = (masses['transient'] + 1) // 2
    relay_mass = max(masses['compute'], normalized_transient)
    overall_mass = max(relay_mass, masses['storage'])
    relay = relay_mass * relay_per_kg // 1000
    relay = min(c.MAX_SOMPI, relay if relay else relay_per_kg)
    required = max(relay, ceiling(Fraction(5, 4) * chosen_rate * overall_mass))
    return overall_mass, relay_mass, relay, required


def load_binding(bundle):
    """Retained literal fixture bytes anchor receipts; PK bytes remain external.

    This is final-body/fee qualification, not a replacement for full parameter
    inspection and independently retained owner intent/setup provenance.
    """
    bundle = Path(bundle)
    raw = (bundle / 'manifest.json').read_bytes()
    manifest = c.load_json(bundle / 'manifest.json')
    branches = {}
    for branch in c.BRANCHES:
        request = c.load_json(bundle / (branch + '.validate.json'))
        c.require(request['transaction'] == c.load_json(bundle / (branch + '.transaction.json')),
                  'retained request/body mismatch')
        names = [branch + suffix for suffix in ('.vk', '.proof', '.context.hex')]
        state = 's1' if branch == 's1_terminal' else 's0'
        names.append(state + '.redeem')
        artifacts = {name: c.sha((bundle / name).read_bytes()) for name in names}
        c.require(artifacts[branch + '.vk'] == manifest['branches'][branch]['vk']['sha256'] and
                  artifacts[state + '.redeem'] == manifest['states'][state]['redeem']['sha256'],
                  'VK/redeem artifact binding')
        context = bytes.fromhex((bundle / (branch + '.context.hex')).read_text().strip())
        c.require(context.hex() == manifest['branches'][branch]['context_hex'] and
                  c.sha(context) == manifest['branches'][branch]['context_sha256'], 'context artifact binding')
        witness = recovery.pushes(bytes.fromhex(request['transaction']['inputs'][0]['signatureScript']))
        c.require(len(witness) == 5 and witness[3].hex() == manifest['branches'][branch]['selector_hex'] and
                  c.sha(witness[2]) == artifacts[branch + '.proof'] and
                  c.sha(witness[4]) == artifacts[state + '.redeem'], 'witness/branch/artifact binding')
        measurement_file = bundle / (branch + '.measurement.json')
        branches[branch] = {'request': request, 'artifacts_sha256': artifacts,
            'measurement_sha256': c.sha(measurement_file.read_bytes()),
            'measurement': json.loads(measurement_file.read_text())}
    return {'manifest': manifest, 'manifest_sha256': c.sha(raw), 'branches': branches}


def check_receipt_binding(manifest, measured, sdk, binding):
    c.require(binding is not None and manifest == binding['manifest'], 'manifest binding mismatch')
    c.require(sdk.get('schema') == 'kpi-a1-sdk-roundtrip/v2' and
              sdk.get('manifest_sha256') == binding['manifest_sha256'], 'SDK manifest hash binding')
    c.require(len(sdk['branches']) == len(c.BRANCHES) and
              {x['branch'] for x in sdk['branches']} == set(c.BRANCHES), 'duplicate/mixed SDK branch records')
    c.require(set(measured['G4_decoded_measurements']) == set(c.BRANCHES), 'measurement branch records')
    records = {x['branch']: x for x in sdk['branches']}
    for branch in c.BRANCHES:
        bound = binding['branches'][branch]; receipt = records[branch]
        tx = bound['request']['transaction']; entry = bound['request']['entry']
        measurement = measured['G4_decoded_measurements'][branch]
        c.require(measurement == bound['measurement'], 'different transaction measurement receipt')
        c.require(receipt.get('decoded_transaction') == tx and receipt.get('input_entry') == entry,
                  'decoded final body/UTXO binding')
        c.require(receipt.get('measurement_sha256') == bound['measurement_sha256'] and
                  receipt.get('artifacts_sha256') == bound['artifacts_sha256'], 'measurement/artifact hash binding')
        state = 's1' if branch == 's1_terminal' else 's0'
        reserve = manifest['states'][state]
        c.require(len(tx['inputs']) == 1 and entry['amount'] == int(reserve['R']) and
                  recovery.rpc_spk(entry['scriptPublicKey']).hex() == reserve['spk_hex'] and
                  entry['covenantId'] is None, 'input reserve binding')
        expected = manifest['branches'][branch]['outputs']
        c.require(len(tx['outputs']) == len(expected) and all(
            actual['value'] == wanted['value'] and actual['scriptPublicKey'] == wanted['spk_hex'] and
            actual['covenant'] is None for actual, wanted in zip(tx['outputs'], expected)), 'output branch binding')
        fee = int(entry['amount']) - sum(int(out['value']) for out in tx['outputs'])
        budget = tx['inputs'][0]['computeBudget']
        c.require(fee == int(manifest['branches'][branch]['fee']) == measurement['fee_sompi'] and
                  receipt['fee_sompi'] == str(fee), 'decoded fee binding')
        c.require(budget == int(manifest['envelope']['compute_budgets'][branch]) == measurement['compute_budget'] ==
                  receipt['compute_budget'], 'decoded budget binding')
        c.require(tx['id'] == measurement['txid'] == receipt['txid'], 'decoded txid binding')
        c.require(recovery.full_hash(tx) == measurement['full_hash'] == receipt['full_hash'], 'decoded full hash binding')
        c.require(receipt['committed_storage_mass'] == tx['storageMass'] == str(measurement['meter']['storage_mass']),
                  'storage commitment binding')
    return records


def revalidate_bodies(binding, sdk, binary):
    """CLI always reruns native Full/masses on the actual SDK-decoded bodies."""
    with tempfile.TemporaryDirectory(prefix='kpi-a1-fee-native-') as tmp:
        request = Path(tmp) / 'request.json'
        for receipt in sdk['branches']:
            request.write_bytes(c.canonical_json({'transaction': receipt['decoded_transaction'], 'entry': receipt['input_entry']}))
            checked = json.loads(subprocess.check_output([str(binary), 'validate-body', str(request)], text=True))
            c.require(checked['full_valid'] is True and checked['txid'] == receipt['txid'] and
                      checked['full_hash'] == receipt['full_hash'] and checked['fee'] == receipt['fee_sompi'] and
                      checked['native_masses'] == receipt['native_masses'], 'fresh native decoded receipt disagreement')


def qualify(manifest, measured, sdk, quote, now, binding=None):
    c.require(quote['network'] == 'testnet-10', 'quote network')
    c.require(quote['pins']['rusty_kaspa_commit'] == manifest['pins']['rusty_kaspa_commit'], 'quote source pin')
    rates = [Fraction(100)]; ages = []
    for observation in quote['observations']:
        c.require(observation['status'] == 'observed' and observation['dag']['network'] == 'testnet-10', 'missing quote')
        c.require(observation['info']['isSynced'] and observation['info']['serverVersion'] == '2.1.0', 'quote node capability')
        stamp = datetime.fromisoformat(observation['observed_at_utc'].replace('Z', '+00:00')).timestamp()
        age = Decimal(str(now)) - Decimal(str(stamp))
        c.require(Decimal(0) <= age <= Decimal(300), 'stale/future quote; recheck before qualification/funding')
        ages.append(str(age))
        estimate = observation['fees']['estimate']
        for bucket in [estimate['priorityBucket']] + estimate['normalBuckets'] + estimate['lowBuckets']:
            rate = Fraction(bucket['feerate'])
            c.require(rate > 0, 'invalid quote rate'); rates.append(rate)
    c.require(len(ages) >= 1, 'no observed quote')
    chosen = max(rates); branches = {}
    sdk_records = check_receipt_binding(manifest, measured, sdk, binding)
    for branch in c.BRANCHES:
        record = measured['G4_decoded_measurements'][branch]
        masses = sdk_records[branch]['native_masses']; meter = record['meter']
        c.require(sdk_records[branch]['native_full_after_decode'], 'decoded Full missing')
        c.require(masses == {'compute': meter['compute_mass'], 'storage': meter['storage_mass'], 'transient': meter['transient_mass']}, 'fresh decoded mass mismatch')
        overall_mass, relay_mass, relay, required = fee_requirements(masses, chosen)
        fee = c.decimal(manifest['branches'][branch]['fee'], monetary=True)
        c.require(fee >= required, 'fee headroom fails: ' + branch)
        units = meter['script_units']; budget = c.decimal(manifest['envelope']['compute_budgets'][branch], 16)
        c.require(budget == (11 * units + 99999) // 100000, 'exact 10-percent budget qualification')
        c.require(masses['compute'] <= 500000 and masses['storage'] <= 500000 and masses['transient'] <= 1000000, 'TN10 hard mass ceiling')
        c.require(record['signature_bytes'] <= 250000 and record['redeem_bytes'] <= 2000, 'signature/G0 script ceiling')
        c.require(all(x <= 10000 for x in record['output_script_bytes']) and meter['peak_combined_stack'] <= 244, 'output/stack ceiling')
        c.require(all(x <= 1000000 for x in meter['native_counted_ops_per_script_signature_spk_redeem']), 'counted ops ceiling')
        branches[branch] = {'relay_fee_mass': str(relay_mass), 'normalized_overall_mass': str(overall_mass),
                            'source_default_relay_floor_sompi': str(relay),
                            'required_with_25_percent_headroom_sompi': str(required),
                            'fixed_fee_sompi': str(fee), 'qualified_budget': str(budget), 'hard_limits_passed': True}
    f0 = c.decimal(manifest['branches']['s0_terminal']['fee'])
    fc = c.decimal(manifest['branches']['s0_continue']['fee'])
    f1 = c.decimal(manifest['branches']['s1_terminal']['fee'])
    b0 = c.decimal(manifest['states']['s0']['B'])
    required_credit = (11 * max(f0, fc + f1) + 9) // 10
    c.require(b0 >= required_credit, 'refundable fee-credit headroom')
    return {'schema': 'kpi-a1-fee-qualification/v2', 'manifest_sha256': binding['manifest_sha256'],
            'sdk_receipt_sha256': c.sha(c.canonical_json(sdk)),
            'measurement_receipt_sha256': c.sha(c.canonical_json(measured)), 'qualified_unix_seconds': str(now),
            'chosen_rate_sompi_per_gram_rational': [str(chosen.numerator), str(chosen.denominator)],
            'estimator_selection': 'conservative maximum of all observed priority/normal/low buckets and source relay minimum; normal baseline included',
            'quote_ages_seconds': ages, 'branches': branches, 'B0': str(b0),
            'required_B0_with_10_percent_refundable_headroom': str(required_credit),
            'scope': 'offline decoded native masses plus fresh quote/source-default relay rules; not admission/config attestation',
            'funding_authorized': False, 'G6_executed': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'measurement', 'sdk', 'quote', 'output'): p.add_argument(name, type=Path)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--validator', type=Path, required=True)
    p.add_argument('--historical-time', type=float, help='Explicit historical replay only; never a current fee quote')
    a = p.parse_args()
    manifest = c.load_json(a.manifest); measurement = json.loads(a.measurement.read_text())
    sdk = json.loads(a.sdk.read_text()); quote = quote_json(a.quote); now = time.time() if a.historical_time is None else a.historical_time
    binding = load_binding(a.bundle)
    result = qualify(manifest, measurement, sdk, quote, now, binding)
    revalidate_bodies(binding, sdk, a.validator)
    if a.historical_time is not None:
        result['scope'] = 'historical quote replay with freshly revalidated decoded bodies; not current fee/admission qualification'
    result.update(native_revalidated=True, validator_binary_sha256=c.sha(a.validator.read_bytes()),
                  historical_quote_replay=a.historical_time is not None, executed_unix_seconds=str(time.time()),
                  quote_file_sha256=c.sha(a.quote.read_bytes()))
    negatives = []
    for name in ('too_high_quote', 'insufficient_refundable_B0', 'wrong_exact_budget', 'expired_quote'):
        altered = copy.deepcopy(manifest); prices = copy.deepcopy(quote); clock = now
        if name == 'too_high_quote': prices['observations'][0]['fees']['estimate']['priorityBucket']['feerate'] = Decimal('1000')
        elif name == 'insufficient_refundable_B0': altered['states']['s0']['B'] = '65999999'
        elif name == 'wrong_exact_budget': altered['envelope']['compute_budgets']['s0_continue'] = '1707'
        else: clock += 301
        try: qualify(altered, measurement, sdk, prices, clock, binding)
        except c.Invalid as error: negatives.append({'case': name, 'rejected': True, 'error': str(error)})
        else: raise c.Invalid('fee/resource negative unexpectedly passed: ' + name)
    result['executed_negative_cases'] = negatives
    result['original_terms_unchanged'] = manifest == c.load_json(a.manifest)
    with a.output.open('xb') as stream: stream.write(c.canonical_json(result))
    print(json.dumps({'qualified': True, 'scope': result['scope'], 'funding_authorized': False}))


if __name__ == '__main__': main()
