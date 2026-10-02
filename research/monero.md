# Monero — Research Notes

## Why study it

Monero is a mature example of privacy integrated into the base currency rather than an optional application pool.

KPI is not trying to turn Kaspa into Monero, but Monero provides important lessons about sender, recipient, amount, and network privacy.

## Relevant concepts

Monero documentation describes:

- ring signatures for sender privacy;
- stealth addresses for recipient privacy;
- RingCT for amount confidentiality;
- Dandelion++ for transaction-propagation privacy;
- optional Tor/I2P practices when stronger network-level privacy is needed.

## Lessons for KPI

### Ledger privacy is not IP privacy

A shielded transaction can still leak identity through network behavior or untrusted remote infrastructure.

### Wallet architecture matters

Using remote nodes can create different privacy assumptions from using a local node.

### Default privacy has different network effects

Monero's base protocol has privacy by default. KPI is intentionally researching optional privacy for KAS, so users crossing the transparent/private boundary create additional correlation challenges.

## Questions

- Which network-level protections are feasible for a Kaspa privacy wallet?
- Should local node use be the strongest recommended mode?
- Can relay schemes improve transaction-submission privacy without a new consensus layer?
- How do optional privacy and default privacy differ in real anonymity-set behavior?

## Primary source

- https://docs.getmonero.org/technical-specs/
