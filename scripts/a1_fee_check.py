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


def qualify(manifest, measured, sdk, quote, now):
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
    sdk_records = {record['branch']: record for record in sdk['branches']}
    c.require(set(sdk_records) == set(c.BRANCHES), 'all final decoded branches required')
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
    return {'schema': 'kpi-a1-fee-qualification/v1', 'qualified_unix_seconds': str(now),
            'chosen_rate_sompi_per_gram_rational': [str(chosen.numerator), str(chosen.denominator)],
            'estimator_selection': 'conservative maximum of all observed priority/normal/low buckets and source relay minimum; normal baseline included',
            'quote_ages_seconds': ages, 'branches': branches, 'B0': str(b0),
            'required_B0_with_10_percent_refundable_headroom': str(required_credit),
            'scope': 'offline decoded native masses plus fresh quote/source-default relay rules; not admission/config attestation',
            'funding_authorized': False, 'G6_executed': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'measurement', 'sdk', 'quote', 'output'): p.add_argument(name, type=Path)
    a = p.parse_args()
    manifest = c.load_json(a.manifest); measurement = json.loads(a.measurement.read_text())
    sdk = json.loads(a.sdk.read_text()); quote = quote_json(a.quote); now = time.time()
    result = qualify(manifest, measurement, sdk, quote, now)
    negatives = []
    for name in ('too_high_quote', 'insufficient_refundable_B0', 'wrong_exact_budget', 'expired_quote'):
        altered = copy.deepcopy(manifest); prices = copy.deepcopy(quote); clock = now
        if name == 'too_high_quote': prices['observations'][0]['fees']['estimate']['priorityBucket']['feerate'] = Decimal('1000')
        elif name == 'insufficient_refundable_B0': altered['states']['s0']['B'] = '65999999'
        elif name == 'wrong_exact_budget': altered['envelope']['compute_budgets']['s0_continue'] = '1707'
        else: clock += 301
        try: qualify(altered, measurement, sdk, prices, clock)
        except c.Invalid as error: negatives.append({'case': name, 'rejected': True, 'error': str(error)})
        else: raise c.Invalid('fee/resource negative unexpectedly passed: ' + name)
    result['executed_negative_cases'] = negatives
    result['original_terms_unchanged'] = manifest == c.load_json(a.manifest)
    with a.output.open('xb') as stream: stream.write(c.canonical_json(result))
    print(json.dumps({'qualified': True, 'scope': result['scope'], 'funding_authorized': False}))


if __name__ == '__main__': main()
