# Security Policy

## Current status

This repository is early research and may contain incomplete designs, unsafe experiments, placeholder code, and unreviewed cryptography.

**Do not use it with real funds.**

## Vulnerability reporting

GitHub Private Vulnerability Reporting is enabled for this repository. Use [Report a vulnerability](https://github.com/olafweller/kaspa-privacy-initiative/security/advisories/new) for sensitive findings. The report is private to repository maintainers and the reporter through GitHub's advisory workflow.

For public discussion:

- do not publish detailed exploit instructions for any experiment that may already be running with value;
- open a public issue only for non-sensitive design/security discussion;
- clearly label suspected critical issues without posting weaponized details.

Never include bearer tokens, private keys, or user wallet secrets in a report. Before any deployment with economic value, document a dedicated contact, response ownership, and incident process as well. This repository currently contains no deployed privacy protocol or real-fund experiment.

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
