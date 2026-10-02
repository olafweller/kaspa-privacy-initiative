# Legal and Operational Questions

**Purpose:** collect questions for qualified counsel and operational design. This document does not provide legal advice.

The technical goal is to minimize trusted control over user funds. That may also change the legal/operational profile, but no legal conclusion should be inferred without professional review.

## Before any mainnet deployment, ask specialist counsel about:

### Software publication

- What legal distinctions exist between publishing open-source privacy software and operating a user-facing financial service?
- Does coordinating protocol development create obligations separate from operating infrastructure?

### Custody and control

- Which technical powers could be interpreted as custody or control?
- Does any emergency/admin key materially change that analysis?
- How does permissionless withdrawal affect the analysis?

### Frontend operation

- Does operating an official website/wallet frontend create a distinct service role?
- How do hosted RPC, state, or relay services change responsibilities?

### Proving/execution infrastructure

- Does operating a hosted prover/executor create obligations that do not apply to publishing prover software?
- Does charging for proof generation change the analysis?

### Fees and protocol revenue

- How should protocol fees be characterized?
- Does a shield/unshield fee paid to a development treasury change the operational role of the project?
- Can protocol fees be routed without giving an organization control over user reserve assets?

### Treasury

- What legal structure, if any, is appropriate for development grants and contributor compensation?
- How should treasury governance remain separate from user funds?

### Project steward compensation

- How can contributors/project stewards be paid transparently without implying custody or ownership of the protocol?

### Jurisdictions

- Which jurisdictions matter for maintainers, hosted infrastructure, foundation/treasury entities, and users?

### Sanctions / abuse response

- Which obligations may apply to entities operating hosted services even if the base protocol is permissionless?
- What should documentation say about legitimate privacy use versus illegal activity without pretending protocol developers can control all downstream use?

## Technical design information counsel will need

Do not ask a lawyer to analyze an abstract "privacy coin." Provide:

- exact custody model;
- exact withdrawal conditions;
- admin/upgrade keys, if any;
- fee flows;
- treasury control;
- frontend architecture;
- prover/executor architecture;
- ability/inability to block users;
- what data operators can see;
- which components are optional and independently hostable.

## Timing

Legal review is not required to write a research specification or isolated testnet PoC.

It becomes increasingly important before:

- mainnet deployment;
- accepting meaningful user funds;
- collecting protocol revenue;
- running hosted services;
- paying ongoing compensation from protocol-generated fees.
