---
description: Provision an ephemeral Azure Windows 11 VM (small/medium/large) for desktop-app testing.
argument-hint: "[small|medium|large]"
---

# /awvm-up — Provision a Windows VM

Spins up a fresh Win11 Pro VM in Azure (~4 min). Single VM at a time per checkout.

## What to run

Parse the size from `$ARGUMENTS` (default `small`) and run:

```bash
cd ~/workspaces/growth/repos/azure-windows && uv run scripts/awvm.py up --size <size>
```

Or use the zsh alias if the user prefers:
- `wup` → small
- `wup-med` → medium
- `wup-lg` → large

## Sizes & rough cost

| Tier | VM | vCPU / RAM | ~$/hr |
|---|---|---|---|
| small | `Standard_B2ms` | 2 / 8 GB | ~$0.13 |
| medium | `Standard_D4s_v5` | 4 / 16 GB | ~$0.30 |
| large | `Standard_D8s_v5` | 8 / 32 GB | ~$0.60 |

Idle cost when destroyed: $0.

## Failure modes the CLI will catch and report

- Not logged into Azure → "run `az login`"
- VM size unavailable / restricted in region → suggests changing region or size
- Windows image SKU not found → suggests `az vm image list` to discover the current SKU
- A live VM already exists in this checkout → tells the user to run `/awvm-status` or `/awvm-down` first

Don't try to recover from these in the skill — surface the CLI's error verbatim. The CLI's messages are authoritative.

## After success

The CLI will:
1. Save credentials to `.azure-windows/credentials.json`
2. Generate `.azure-windows/connect.rdp`
3. Auto-open the `.rdp` file in Windows App (or print a path if the app isn't installed)

The operator should then double-click the .rdp file (or wait for Windows App to prompt) and type the password from the CLI output to RDP in.
