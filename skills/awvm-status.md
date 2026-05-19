---
description: Show current Azure Windows VM state — healthy, absent, or drifted — with uptime and rough cost.
---

# /awvm-status — Current VM state

Reports one of three states for the VM in this checkout:

| State | Meaning |
|---|---|
| `healthy` | tfstate and local metadata agree; VM is real |
| `absent` | no tfstate, no metadata — nothing provisioned |
| `drifted` | one side has state, the other doesn't — manual recovery needed |

For healthy VMs, also shows: run_id, size, region, RG name, VM name, public IP, allowed CIDR, admin username, created timestamp, uptime, and a clearly labeled rough spend estimate.

## What to run

```bash
cd ~/workspaces/growth/repos/azure-windows && uv run scripts/awvm.py status
```

Or use the zsh alias: `wstatus`.

## On `drifted`

Surface the CLI's recovery hints verbatim and point the user at `docs/RECOVERY.md`. Drift typically means one of:

- Local metadata was wiped but Azure resources still exist → use `az group delete` then `awvm down --force-clean-local`.
- tfstate exists but local metadata doesn't → run `awvm down --yes`; the CLI rebuilds the required `-var` values from terraform outputs.

Do not assume "drifted" is safe to ignore — there may be Azure resources silently accruing cost.
