"""Executable economic/role model, NOT a cryptographic payment protocol.

ProofOracle models a sound proof predicate. Its registry is a test abstraction,
not a server-supplied valid flag. Hash/HMAC encodings below are model identifiers,
not a selected production note/nullifier construction. No network or real keys.
"""
from dataclasses import dataclass, field
import copy
import hashlib
import hmac
import json
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import CryptoError

MAX = (1 << 64) - 1
NETWORK, POOL, VERSION = 'testnet-10', 'KPI-LOCAL-MODEL-ONLY', 1


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def hash_id(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def amount(value):
    if type(value) is not int or not 0 <= value <= MAX:
        raise ValueError('integer sompi/range')
    return value


def total(values):
    return amount(sum(amount(v) for v in values))


@dataclass(frozen=True)
class Note:
    owner: str
    value: int
    randomness: str

    def __post_init__(self):
        amount(self.value)
        if self.value == 0 or len(bytes.fromhex(self.owner)) != 32 or len(bytes.fromhex(self.randomness)) != 32:
            raise ValueError('model note format')

    @property
    def commitment(self):
        return hash_id(['MODEL-NOTE', NETWORK, POOL, self.owner, self.value, self.randomness])

    def public(self, recipient):
        if self.owner != recipient.owner:
            raise ValueError('recipient ownership mismatch')
        VerifyKey(bytes.fromhex(recipient.owner)).verify(
            canonical(['MODEL-RECEIVE', NETWORK, POOL, recipient.owner, recipient.incoming]),
            bytes.fromhex(recipient.signature))
        # Fixed-width model note encoding avoids value-digit-length ciphertext leakage.
        raw = canonical({**self.__dict__, 'value': format(self.value, '016x')})
        cipher = bytes(SealedBox(PublicKey(bytes.fromhex(recipient.incoming))).encrypt(raw)).hex()
        return {'commitment': self.commitment, 'ciphertext': cipher}


@dataclass(frozen=True)
class Recipient:
    owner: str
    incoming: str
    signature: str


class Wallet:
    def __init__(self, test_name):
        # Deliberately reproducible PUBLIC TEST FIXTURES, never usable for funding.
        self._spend = SigningKey(hashlib.sha256(('MODEL-SPEND:' + test_name).encode()).digest())
        self._view = PrivateKey(hashlib.sha256(('MODEL-VIEW:' + test_name).encode()).digest())
        self.owner = bytes(self._spend.verify_key).hex()
        incoming = bytes(self._view.public_key).hex()
        signature = self.sign(['MODEL-RECEIVE', NETWORK, POOL, self.owner, incoming])
        self.address = Recipient(self.owner, incoming, signature)

    def note(self, value, label):
        return Note(self.owner, amount(value), hash_id(['MODEL-RANDOMNESS', self.owner, label]))

    def nullifier(self, note):
        if note.owner != self.owner:
            raise ValueError('unauthorized spending key')
        # Economic domain is stable across statement/verifier versions.
        return hmac.new(bytes(self._spend), canonical(['MODEL-NF', NETWORK, POOL, note.commitment]), hashlib.sha256).hexdigest()

    def sign(self, body):
        return self._spend.sign(canonical(body)).signature.hex()

    def discover(self, public_outputs):
        result = []
        for output in public_outputs:
            try:
                data = SealedBox(self._view).decrypt(bytes.fromhex(output['ciphertext']))
                fields = json.loads(data)
                fields['value'] = int(fields['value'], 16)
                note = Note(**fields)
                if note.owner == self.owner and note.commitment == output['commitment']:
                    result.append(note)
            except (ValueError, TypeError, KeyError, CryptoError):
                # Discovery errors cannot create a balance or a spendable note.
                # The model skips unauthenticated/unrelated ciphertexts.
                continue
        return result


@dataclass
class Proof:
    public: dict
    token: str


class ProofOracle:
    """Explicit ideal proof functionality, not real ZK and not deployable."""
    def __init__(self):
        self._registered = {}

    def _register(self, public):
        token = hash_id(['MODEL-PROOF', public])
        self._registered[token] = canonical(public)
        return Proof(copy.deepcopy(public), token)

    def verify(self, proof):
        if not isinstance(proof, Proof) or self._registered.get(proof.token) != canonical(proof.public):
            raise ValueError('invalid model proof')
        return copy.deepcopy(proof.public)

    def credit(self, event, note, recipient):
        if event['commitment'] != note.commitment or note.value != event['amount']:
            raise ValueError('deposit statement binding')
        return self._register({'kind': 'credit', 'network': NETWORK, 'pool': POOL, 'version': VERSION,
                               'deposit': event['id'], 'outputs': [note.public(recipient)]})

    def spend(self, wallet, notes, outputs, snapshot, withdrawal=None, fee=0, fee_recipient='model-relayer'):
        commitments = [n.commitment for n in notes]
        if not notes or len(set(commitments)) != len(commitments):
            raise ValueError('duplicate/missing input')
        if any(c not in snapshot for c in commitments):
            raise ValueError('input membership')
        nullifiers = [wallet.nullifier(n) for n in notes]
        withdrawal = withdrawal or {'recipient': '', 'amount': 0}
        fee, exit_value = amount(fee), amount(withdrawal['amount'])
        if exit_value and not withdrawal['recipient']:
            raise ValueError('missing payout recipient')
        if total(n.value for n in notes) != total([*(n.value for n, _ in outputs), exit_value, fee]):
            raise ValueError('value conservation')
        public = {'kind': 'spend', 'network': NETWORK, 'pool': POOL, 'version': VERSION,
                  'anchor': hash_id(snapshot), 'nullifiers': nullifiers,
                  'outputs': [n.public(r) for n, r in outputs], 'withdrawal': withdrawal,
                  'fee': fee, 'fee_recipient': fee_recipient}
        # Authority is checked here, inside the modelled wallet predicate.
        VerifyKey(bytes.fromhex(wallet.owner)).verify(canonical(public), bytes.fromhex(wallet.sign(public)))
        return self._register(public)


@dataclass
class Pool:
    verifier: ProofOracle
    commitments: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    anchors: dict = field(default_factory=dict)
    nullifiers: set = field(default_factory=set)
    deposits: dict = field(default_factory=dict)
    claims: dict = field(default_factory=dict)
    fees: dict = field(default_factory=dict)
    processed: set = field(default_factory=set)
    outcomes: list = field(default_factory=list)
    reserve: int = 0
    rent_reserve: int = 0
    rent_sponsor_available: int = 0
    rent_external_funded: int = 0
    rent_paid: int = 0
    private_total: int = 0

    def __post_init__(self):
        self._anchor()

    def _anchor(self):
        self.anchors[hash_id(self.commitments)] = list(self.commitments)

    def funded_deposit(self, identity, note, refund_wallet):
        """Model a validated native event, not an RPC/payment-existence check."""
        if identity in self.deposits:
            raise ValueError('duplicate native deposit')
        event = {'id': identity, 'amount': note.value, 'commitment': note.commitment,
                 'refund_owner': refund_wallet.owner, 'state': 'pending'}
        next_reserve = total([self.reserve, note.value])
        self.deposits[identity] = event
        self.reserve = next_reserve
        self.invariant()
        return copy.deepcopy(event)

    def invariant(self):
        pending = total(d['amount'] for d in self.deposits.values() if d['state'] == 'pending')
        unpaid = total(c['amount'] for c in self.claims.values() if not c['paid'])
        fees = total(f['amount'] for f in self.fees.values() if not f['paid'])
        assert self.reserve == total([self.private_total, pending, unpaid, fees])
        assert self.rent_reserve == total(c['rent'] for c in self.claims.values() if not c['paid'])
        assert self.rent_external_funded == total([self.rent_sponsor_available, self.rent_reserve, self.rent_paid])
        return {'reserve': self.reserve, 'private': self.private_total, 'pendingDeposits': pending,
                'unpaidExits': unpaid, 'unpaidFees': fees, 'rentReserve': self.rent_reserve}

    def fund_rent(self, value):
        """Explicit model-native external funding; uncommitted funds are not backing."""
        value = amount(value)
        available = total([self.rent_sponsor_available, value])
        funded = total([self.rent_external_funded, value])
        self.rent_sponsor_available, self.rent_external_funded = available, funded
        self.invariant()

    def process(self, proof, host_claim=None):
        """Canonical ordered application. A host verdict cannot decide validity."""
        try:
            p = self.verifier.verify(proof)
            if type(p['version']) is not int or (p['network'], p['pool'], p['version']) != (NETWORK, POOL, VERSION):
                raise ValueError('network/pool/statement version')
            identity = hash_id(p)
            if identity in self.processed:
                raise ValueError('operation replay')
            new = [o['commitment'] for o in p['outputs']]
            if len(new) != len(set(new)) or any(c in self.commitments for c in new):
                raise ValueError('duplicate output commitment')
            if p['kind'] == 'credit':
                event = self.deposits[p['deposit']]
                if event['state'] != 'pending' or new != [event['commitment']]:
                    raise ValueError('deposit absent/spent/wrong commitment')
                next_total = total([self.private_total, event['amount']])
                nf, withdrawal, fee = [], None, 0
            elif p['kind'] == 'spend':
                if p['anchor'] not in self.anchors:
                    raise ValueError('unknown membership anchor')
                nf = p['nullifiers']
                if not nf or len(nf) != len(set(nf)) or any(n in self.nullifiers for n in nf):
                    raise ValueError('nullifier already spent/duplicated')
                withdrawal, fee = p['withdrawal'], amount(p['fee'])
                exit_value = amount(withdrawal['amount'])
                debit = total([exit_value, fee])
                if debit > self.private_total:
                    raise ValueError('aggregate liability underflow')
                next_total = self.private_total - debit
                if exit_value:
                    total([self.rent_reserve, 50_000_000])
                    if self.rent_sponsor_available < 50_000_000:
                        raise ValueError('permission rent not funded')
            else:
                raise ValueError('operation kind')
            # Commit only after ALL checks; rejected operations update no economic state.
            self.private_total = next_total
            if p['kind'] == 'credit':
                self.deposits[p['deposit']]['state'] = 'credited'
            self.nullifiers.update(nf)
            self.commitments.extend(new); self.outputs.extend(copy.deepcopy(p['outputs']))
            if withdrawal and withdrawal['amount']:
                self.claims[identity] = {**withdrawal, 'rent': 50_000_000, 'paid': False}
                self.rent_sponsor_available -= 50_000_000
                self.rent_reserve += 50_000_000
            if fee:
                self.fees[identity] = {'amount': fee, 'recipient': p['fee_recipient'], 'paid': False}
            self.processed.add(identity); self._anchor(); self.invariant()
            outcome = {'id': identity, 'accepted': True}
        except (ValueError, KeyError, TypeError) as error:
            outcome = {'id': hash_id(getattr(proof, 'public', {})), 'accepted': False, 'reason': str(error)}
        self.outcomes.append(outcome)
        return outcome

    def refund(self, identity, signature):
        event = self.deposits[identity]
        if event['state'] != 'pending':
            raise ValueError('deposit already consumed')
        body = ['MODEL-REFUND', NETWORK, POOL, identity]
        VerifyKey(bytes.fromhex(event['refund_owner'])).verify(canonical(body), bytes.fromhex(signature))
        event['state'] = 'refunded'; self.reserve -= event['amount']; self.invariant()
        return event['amount']

    def payout(self, identity, recipient, principal, rent, remaining_reserve):
        claim = self.claims[identity]
        if claim['paid'] or (recipient, amount(principal), amount(rent), amount(remaining_reserve)) != (
                claim['recipient'], claim['amount'], claim['rent'], self.reserve - claim['amount']):
            raise ValueError('payout recipient/principal/rent/reserve/spent claim')
        # Validate the full native output before committing any economic changes.
        payout_value = total([principal, rent])
        claim['paid'] = True; self.reserve = remaining_reserve; self.rent_reserve -= rent
        self.rent_paid += rent
        self.invariant(); return payout_value

    def pay_fee(self, identity, recipient, value):
        claim = self.fees[identity]
        if claim['paid'] or (recipient, amount(value)) != (claim['recipient'], claim['amount']):
            raise ValueError('fee recipient/value/replay')
        claim['paid'] = True; self.reserve -= value; self.invariant()
        return value
