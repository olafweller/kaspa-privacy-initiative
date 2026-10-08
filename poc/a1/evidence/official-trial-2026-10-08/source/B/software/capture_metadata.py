"""Infrastructure JSON only; protocol JSON retains a1_check's integer-only reader.

The C checkpoint has fractional wall-clock observation timestamps. They are
metadata, never amounts, indices, sequence numbers, scores or proof inputs.
"""
from decimal import Decimal
import hashlib
import json
from pathlib import Path

TIMESTAMPS = {
    ('coverage', 'at'), ('coverage', 'current', 'at'),
    ('pre_seal_coverage', 'at'), ('pre_seal_coverage', 'current', 'at'),
    ('page_committed_at',), ('sealed_at',),
    ('pre_seal_observation', 'at'), ('selected_observation', 'at'),
}

def load_capture_metadata(path, purpose, expected_sha256=None):
    if purpose not in {'checkpoint', 'source', 'config'}:
        raise ValueError('capture metadata purpose not allowlisted')
    raw = Path(path).read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('capture metadata exceeds bounded document size')
    if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('capture metadata frozen hash mismatch')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate capture metadata key: ' + key)
            result[key] = value
        return result
    def bad_constant(value):
        raise ValueError('nonfinite capture metadata number forbidden')
    value = json.loads(raw, object_pairs_hook=unique, parse_float=Decimal,
                       parse_constant=bad_constant)
    prefix = () if purpose == 'checkpoint' else ('checkpoint',)
    allowed = {prefix + p for p in TIMESTAMPS}
    def normalize(item, location=()):
        if isinstance(item, Decimal):
            if location not in allowed or not item.is_finite() or not 0 <= item <= 2**53:
                raise ValueError('fractional number outside approved timestamp: ' + '.'.join(map(str, location)))
            return float(item)
        if isinstance(item, dict):
            return {k: normalize(v, location + (k,)) for k, v in item.items()}
        if isinstance(item, list):
            return [normalize(v, location + (i,)) for i, v in enumerate(item)]
        return item
    result = normalize(value)
    if purpose == 'config' and result.get('mode') == 'fixture':
        # Keep the established integer-only synthetic config contract.
        import a1_check
        return a1_check.load_json(path)
    checkpoint = result if purpose == 'checkpoint' else result.get('checkpoint')
    if not isinstance(checkpoint, dict):
        raise ValueError('capture checkpoint object missing')
    seq = checkpoint.get('seq')
    if type(seq) is not int or not 0 <= seq < 2**63:
        raise ValueError('capture sequence requires bounded exact integer')
    for key in ['cursor', 'digest']:
        text = checkpoint.get(key)
        if not isinstance(text, str) or len(text) != 64 or any(c not in '0123456789abcdef' for c in text):
            raise ValueError('capture checkpoint ' + key + ' malformed')
    if checkpoint.get('network') != 'testnet-10':
        raise ValueError('capture checkpoint network mismatch')
    return result
