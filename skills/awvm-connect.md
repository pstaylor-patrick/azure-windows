---
description: Reprint creds for the live Windows VM and open RDP via Windows App. No Azure API calls.
---

# /awvm-connect — Open RDP to the running VM

Reads `.azure-windows/credentials.json` (written during `/awvm-up`), prints the IP/username/password table, regenerates `.azure-windows/connect.rdp`, and opens it in Windows App (or legacy Microsoft Remote Desktop if Windows App is not installed).

## What to run

```bash
cd ~/workspaces/growth/repos/azure-windows && uv run scripts/awvm.py connect
```

Or use the zsh alias: `wconnect`.

## Why this avoids Azure API calls

By design — once `/awvm-up` succeeds, `.azure-windows/credentials.json` is sufficient to reconnect. The CLI does not need a live `az` session for `connect`, `rdp`, or `ip`. This means you can RDP even if your Azure CLI session has expired, as long as the VM is still running.

## If RDP fails to connect

Most common cause: your residential public IP rotated and the NSG rule is stale. Run `/awvm-refresh-ip` to re-pin the rule to your current IP.

Next most common: the VM auto-shutdown fired at 02:00 ET. Start it back up:
```bash
az vm start --resource-group <rg_name> --name <vm_name>
```

If neither helps, run `/awvm-status` to confirm the VM still exists.
