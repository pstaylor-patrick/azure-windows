# azure-windows

Ephemeral Windows 11 VMs on Azure for desktop-app testing from a Mac.
Optimized for **fast up/down, minimal idle cost, single-user, throwaway**.

## What this gives you

- `awvm up --size small|medium|large` — provisions a fresh Windows 11 VM in ~5–8 minutes, opens an RDP file pointed at it.
- `awvm down --yes` — destroys everything. $0 idle cost.
- Auto-shutdown at 02:00 ET as a safety net in case you forget to `down`.
- One live VM at a time per checkout. Truly ephemeral — every spin-up is fresh.

## Sizes & rough cost

| Tier | VM | vCPU / RAM | ~$/hr (Windows incl.) |
|---|---|---|---|
| small | `Standard_B2ms` | 2 / 8 GB | ~$0.13 |
| medium | `Standard_D4s_v5` | 4 / 16 GB | ~$0.30 |
| large | `Standard_D8s_v5` | 8 / 32 GB | ~$0.60 |

OS disk (Standard SSD, 128 GB) and public IP add a few cents/hr. Idle cost when destroyed: **$0**.

Cost numbers are planning estimates, not billing truth.

## One-time setup

```bash
brew install azure-cli terraform uv
# Install Windows App (formerly Microsoft Remote Desktop) from the Mac App Store:
# https://apps.apple.com/app/windows-app/id1295203466
az login

# Install Claude Code skills (/awvm, /awvm-up, etc.)
./install.sh
```

Uninstall the skills any time with `./install.sh --uninstall`. The script
symlinks files from `skills/` into `~/.claude/commands/`, so edits to the
source files take effect immediately.

### Optional: zsh aliases

```bash
awvm() {
  ( cd ~/workspaces/growth/repos/azure-windows && uv run scripts/awvm.py "$@" )
}
alias wup='awvm up --size small'
alias wdown='awvm down --yes'
alias wstatus='awvm status'
alias wconnect='awvm connect'
alias wrefresh='awvm allow-ip-refresh'
```

Confirm you're on the right subscription:

```bash
az account show
# If you have multiple:
az account list -o table
az account set --subscription <id>
```

## Daily use

```bash
# Spin up
uv run scripts/awvm.py up --size small

# Check state
uv run scripts/awvm.py status

# Re-open RDP from saved creds (no Azure API calls)
uv run scripts/awvm.py connect

# Tear down
uv run scripts/awvm.py down --yes
```

## When your home IP changes

If RDP stops working mid-session because your residential IP rotated:

```bash
uv run scripts/awvm.py allow-ip-refresh
```

This detects your current public IP and updates the NSG rule in place — no rebuild needed.

## Files

```
.github/CODEOWNERS                # @pstaylor-patrick owns everything
.claude/commands/awvm.md          # Claude Code slash command (thin dispatcher)
scripts/awvm.py                   # Typer CLI — all real logic
terraform/                        # RG + vnet + NSG + Win11 VM + auto-shutdown
docs/RECOVERY.md                  # What to do when apply/destroy half-fails
.azure-windows/                   # Local runtime state (gitignored)
```

## Design invariants

- **Python is the control plane.** It owns `run_id`, password generation, local metadata, and orchestration. Terraform only provisions what Python tells it to provision.
- **One live VM per checkout.** Local state is authoritative.
- **Destroy means destroy.** No "stopped/deallocated" intermediate state in v1.
- **Local metadata is sufficient to reconnect** — `connect` and `rdp` make no Azure API calls.
- **All cloud assumptions are validated at runtime.** Region availability, quota, and image resolvability are preflight checks, not hard-coded hopes.

## Non-goals (v1)

- Remote tfstate (single user, single laptop)
- Multi-VM fleets
- Data disks / persistence across spin-ups
- `custom_data` provisioning scripts (no auto-installed apps)
- Bastion, Key Vault, Private Link
- Cost dashboards

## When something goes wrong

See [docs/RECOVERY.md](docs/RECOVERY.md).
