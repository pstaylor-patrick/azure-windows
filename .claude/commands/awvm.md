---
description: Spin up / spin down ephemeral Azure Windows VMs for desktop-app testing.
argument-hint: "up [small|medium|large] | down [--yes] | status | connect | ip | rdp | allow-ip-refresh"
---

# /awvm — Ephemeral Azure Windows VMs

Thin dispatcher over `scripts/awvm.py`. All real logic lives in the Python CLI; this skill just maps natural-language intent to the right subcommand.

## Quick reference

| User asks for… | Run |
|---|---|
| Spin up small / medium / large VM | `uv run scripts/awvm.py up --size small\|medium\|large` |
| Tear down the VM | `uv run scripts/awvm.py down --yes` |
| Show current state, uptime, rough cost | `uv run scripts/awvm.py status` |
| Reprint creds and open RDP | `uv run scripts/awvm.py connect` |
| Just the public IP | `uv run scripts/awvm.py ip` |
| Re-open the .rdp file | `uv run scripts/awvm.py rdp` |
| RDP broken after IP change at home | `uv run scripts/awvm.py allow-ip-refresh` |

Default size is `small` if the user doesn't say.

## Preflight contract

Before any command, if the user has clearly never run `up` in this checkout (no `.azure-windows/credentials.json`, no `terraform/.terraform/`), remind them of the one-time setup in `README.md`:

1. `brew install azure-cli terraform`
2. Install Microsoft Remote Desktop from the Mac App Store
3. `az login`

If `az account show` fails inside the CLI, the script already prints a clear "run `az login`" message — surface that verbatim, don't paraphrase.

## What I should NOT do here

- Don't re-implement preflight checks. The Python CLI owns them.
- Don't read `.azure-windows/credentials.json` and print credentials to the user — invoke `awvm connect` instead, which uses the same code path the operator uses normally.
- Don't shell out to `terraform` or `az` directly. Always go through `scripts/awvm.py`.
- Don't push to GitHub or create PRs from this skill.

## Recovery

If `awvm status` reports `drifted`, follow the on-screen instructions. If the operator describes a partial-apply failure (resources in Azure but no local metadata), point them to `docs/RECOVERY.md`.
