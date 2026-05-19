---
description: Umbrella reference for ephemeral Azure Windows VMs — see /awvm-up, /awvm-down, /awvm-connect, /awvm-status, /awvm-refresh-ip.
---

# /awvm — Azure Windows VM cheatsheet

Thin dispatcher family over `scripts/awvm.py` (and the matching zsh aliases). All real logic lives in the Python CLI; these skills just map natural-language intent to the right subcommand.

## When to invoke which sub-skill

| User asks for… | Skill | CLI fallback |
|---|---|---|
| Spin up a Windows VM | `/awvm-up [small\|medium\|large]` | `awvm up --size <tier>` |
| Tear it down | `/awvm-down` | `awvm down --yes` |
| What's the state, IP, cost? | `/awvm-status` | `awvm status` |
| Open RDP / reprint creds | `/awvm-connect` | `awvm connect` |
| RDP broke after home IP change | `/awvm-refresh-ip` | `awvm allow-ip-refresh` |

Default size is `small` when the user doesn't specify.

## Preflight contract

If `az account show` fails inside the CLI, surface the script's "run `az login`" message verbatim — don't paraphrase.

The Python CLI owns all preflight: it validates Azure auth, region availability of the requested SKU, marketplace image resolution, and quota. Don't re-implement any of that here.

## What I should NOT do

- Don't shell out to `terraform` or `az` directly. Always go through `scripts/awvm.py` (or the zsh `awvm` function / `w*` aliases).
- Don't read `.azure-windows/credentials.json` and print credentials inline. Invoke `awvm connect` instead.
- Don't push to GitHub or create PRs from this skill family unless explicitly asked.

## Recovery

If `awvm status` reports `drifted`, follow the on-screen instructions. For partial-apply or partial-destroy failures, point the operator at `docs/RECOVERY.md` in the repo.
