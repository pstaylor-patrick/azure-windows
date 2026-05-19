---
description: Update the NSG RDP rule to your current public IP — fixes RDP after your residential IP rotates.
---

# /awvm-refresh-ip — Re-pin NSG to current public IP

Residential IPs rotate. When the NSG rule no longer matches your current public IP, RDP stops connecting. This skill detects your current IP via ipify, patches the NSG rule in place via `az network nsg rule update`, and refreshes the local metadata.

No VM rebuild required. No Terraform apply. ~3 seconds end-to-end.

## What to run

```bash
cd ~/workspaces/growth/repos/azure-windows && uv run scripts/awvm.py allow-ip-refresh
```

Or use the zsh alias: `wrefresh`.

## When this is the right answer

- RDP just stopped working after you switched networks (home → coffee shop, VPN on/off).
- `nc -zv -w 5 <vm-ip> 3389` times out from your current machine but the VM is still `healthy` per `/awvm-status`.

## When this is NOT the right answer

- The VM was auto-shutdown at 02:00 ET — start it with `az vm start` instead.
- The VM was destroyed — run `/awvm-up` to provision a new one.
- `/awvm-status` reports `absent` — nothing to refresh.
