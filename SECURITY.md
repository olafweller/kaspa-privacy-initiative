# Security Policy

## Current status

This repository is early research and may contain incomplete designs, unsafe experiments, placeholder code, and unreviewed cryptography.

**Do not use it with real funds.**

## Vulnerability reporting

Before any code is deployed with economic value, the repository should enable GitHub Private Vulnerability Reporting / Security Advisories and publish a dedicated private security contact.

Until that channel exists:

- do not publish detailed exploit instructions for any experiment that may already be running with value;
- open a public issue only for non-sensitive design/security discussion;
- clearly label suspected critical issues without posting weaponized details.

## What counts as critical

Examples include:

- unbacked value creation;
- double-spending;
- unauthorized withdrawal;
- proof-verification bypass;
- key or note-ownership bypass;
- reserve-draining conditions;
- permanent loss of valid user funds;
- privacy breaks that deanonymize past users;
- upgrade mechanisms that unexpectedly create confiscation authority.

## Audit expectations

Before any mainnet candidate:

1. protocol specification review;
2. circuit/proof-system review;
3. settlement/withdrawal review;
4. independent implementation testing or test-vector validation;
5. wallet privacy review;
6. infrastructure/liveness review;
7. external security audit(s);
8. public testnet period;
9. bug-bounty plan.

AI review and internal contributor review are useful but do not replace independent specialist review.
