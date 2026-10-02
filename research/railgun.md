# RAILGUN — Research Notes

## Why study it

RAILGUN is directly relevant because it creates private balances and private transfers for assets that originate on otherwise transparent chains.

That is conceptually closer to the KPI goal than creating a separate privacy coin.

## Relevant concepts

RAILGUN describes:

- shielding public assets into private balances;
- hiding sender, recipient, token type, and amount for internal private interactions;
- non-custodial use;
- wallet-level private addresses;
- broadcasters/relays for transaction-submission privacy;
- a privacy set that benefits from more users, shielding activity, and private volume.

## Lessons for KPI

### Existing assets + private claims is an established design pattern

The user does not need a separate speculative privacy asset in order to use private balances. This is design experience from an existing system, not evidence that a Kaspa implementation is secure or feasible.

### Internal use matters

Privacy improves when users can remain inside the private system rather than immediately shield and unshield.

### Relaying matters

Ledger privacy can be undermined if transaction submission directly identifies the sender.

### TVL is not the same as anonymity

A large reserve helps, but transaction count, number of users, timing patterns, and private activity are also important.

## Questions before reuse

- Which RAILGUN assumptions depend on EVM smart contracts?
- Which privacy-set metrics would make sense for KAS?
- How does RAILGUN handle note discovery and broadcaster trust?
- Which fee patterns affect privacy?

## Primary sources

- https://docs.railgun.org/wiki/learn/privacy-system
- https://docs.railgun.org/wiki/learn/shielding-tokens
- https://docs.railgun.org/developer-guide/wallet/transactions/private-transfers
