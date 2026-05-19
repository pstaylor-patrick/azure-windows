---
description: Destroy the current ephemeral Azure Windows VM and all of its resources. Irreversible.
---

# /awvm-down — Destroy the Windows VM

Runs `terraform destroy` for everything in the active resource group (VM, vnet, NSG, public IP, OS disk, auto-shutdown schedule). Idle cost drops to $0.

## What to run

```bash
cd ~/workspaces/growth/repos/azure-windows && uv run scripts/awvm.py down --yes
```

Or use the zsh alias: `wdown`.

`--yes` is baked in because the skill is a deliberate "destroy now" action. If the user wants a confirmation prompt, drop the flag.

## After success

- Resource group deleted from Azure
- `.azure-windows/credentials.json`, `.azure-windows/last_run_id`, and `.azure-windows/connect.rdp` removed locally
- Subsequent `/awvm-status` reports `absent`

## If destroy fails

The CLI exits non-zero and prints the resource group name. Surface that to the user verbatim and point them at `docs/RECOVERY.md` in the repo, or suggest:

```bash
az group delete --name <rg_name> --yes
uv run scripts/awvm.py down --yes --force-clean-local
```

Do not silently wipe local metadata on a failed destroy — the operator may need it to find orphaned resources.
