"""awvm — Ephemeral Azure Windows VMs for desktop-app testing.

Python is the control plane: it owns run_id, password generation, local metadata,
and orchestration. Terraform only provisions what Python tells it to provision.

Usage:
    uv run scripts/awvm.py up [--size small|medium|large] [--region eastus2]
    uv run scripts/awvm.py down [--yes] [--force-clean-local]
    uv run scripts/awvm.py status
    uv run scripts/awvm.py connect
    uv run scripts/awvm.py ip
    uv run scripts/awvm.py rdp
    uv run scripts/awvm.py allow-ip-refresh
"""

from __future__ import annotations

import datetime as dt
import json
import os
import secrets
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
import typer
from rich.console import Console
from rich.table import Table

# Repo-relative paths. The CLI is invoked as `uv run scripts/awvm.py ...`,
# so REPO_ROOT is the parent of scripts/.
REPO_ROOT = Path(__file__).resolve().parent.parent
TF_DIR = REPO_ROOT / "terraform"
STATE_DIR = REPO_ROOT / ".azure-windows"
CRED_FILE = STATE_DIR / "credentials.json"
RUN_POINTER = STATE_DIR / "last_run_id"
RDP_FILE = STATE_DIR / "connect.rdp"

# Rough hourly cost estimates for status display. Planning numbers only.
# Source: Azure public list price for Windows VMs in eastus2 as of 2026-05.
HOURLY_COST_USD = {
    "small": 0.13,
    "medium": 0.30,
    "large": 0.60,
}

VALID_SIZES = ("small", "medium", "large")

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)
console = Console()


# ---------------------------------------------------------------------------
# Metadata model
# ---------------------------------------------------------------------------

@dataclass
class Credentials:
    run_id: str
    size: str
    region: str
    rg_name: str
    vm_name: str
    nsg_name: str
    public_ip: str
    username: str
    password: str
    allowed_cidr: str
    created_at: str

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> "Credentials":
        return cls(**data)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _run(
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    capture: bool = False,
    env_overrides: Optional[dict] = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a subprocess. By default streams to the terminal."""
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=check,
        text=True,
        capture_output=capture,
    )


def _which_or_die(binary: str, install_hint: str) -> None:
    if shutil.which(binary) is None:
        console.print(f"[red]Missing dependency:[/red] {binary}")
        console.print(f"  Install: {install_hint}")
        raise typer.Exit(2)


def _detect_public_ip() -> str:
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            ip = resp.text.strip()
            # Minimal validation — not full IPv4 regex, just sanity.
            if ip.count(".") == 3 and all(p.isdigit() for p in ip.split(".")):
                return ip
        except requests.RequestException:
            continue
    console.print("[red]Could not detect your public IP via ipify or ifconfig.me.[/red]")
    raise typer.Exit(3)


def _generate_password() -> str:
    """Generate a 24-char password that satisfies Windows complexity requirements."""
    # Azure requires 3 of: upper, lower, digit, special. We ensure all 4.
    upper = secrets.choice(string.ascii_uppercase)
    lower = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    special = secrets.choice("!@#$%^&*()-_=+")
    pool = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    rest = "".join(secrets.choice(pool) for _ in range(20))
    chars = list(upper + lower + digit + special + rest)
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def _generate_run_id() -> str:
    """4-char lowercase alphanumeric. ~1.6M combinations — plenty for ephemeral use."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(4))


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def _preflight_tools() -> None:
    _which_or_die("az", "brew install azure-cli")
    _which_or_die("terraform", "brew install terraform")


def _preflight_azure() -> dict:
    """Return the logged-in Azure subscription info, or exit with guidance."""
    try:
        result = _run(["az", "account", "show", "-o", "json"], capture=True, check=True)
    except subprocess.CalledProcessError:
        console.print("[red]Azure CLI is not logged in.[/red]")
        console.print("  Run: [bold]az login[/bold]")
        raise typer.Exit(4)
    return json.loads(result.stdout)


def _preflight_size_in_region(size_sku: str, region: str) -> None:
    """Confirm the VM SKU is offered (and not restricted) in the region."""
    try:
        result = _run(
            [
                "az", "vm", "list-skus",
                "--location", region,
                "--size", size_sku,
                "--query", "[?name=='" + size_sku + "'] | [0]",
                "-o", "json",
            ],
            capture=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to query VM SKUs in {region}:[/red] {e.stderr}")
        raise typer.Exit(5)

    if not result.stdout.strip() or result.stdout.strip() == "null":
        console.print(f"[red]VM size {size_sku} is not offered in {region}.[/red]")
        console.print("  Try a different region or size.")
        raise typer.Exit(5)

    sku_info = json.loads(result.stdout)
    restrictions = sku_info.get("restrictions") or []
    if restrictions:
        reasons = [r.get("reasonCode", "Unknown") for r in restrictions]
        console.print(
            f"[red]VM size {size_sku} is restricted in {region}:[/red] {', '.join(reasons)}"
        )
        raise typer.Exit(5)


def _preflight_image(region: str, publisher: str, offer: str, sku: str) -> None:
    """Confirm the marketplace image SKU resolves in the region."""
    try:
        result = _run(
            [
                "az", "vm", "image", "list",
                "--location", region,
                "--publisher", publisher,
                "--offer", offer,
                "--sku", sku,
                "--all",
                "--query", "[0]",
                "-o", "json",
            ],
            capture=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to query marketplace image:[/red] {e.stderr}")
        raise typer.Exit(6)

    if not result.stdout.strip() or result.stdout.strip() == "null":
        console.print(
            f"[red]Image {publisher}/{offer}/{sku} not found in {region}.[/red]"
        )
        console.print(
            "  List available SKUs:\n"
            f"    az vm image list --location {region} --publisher {publisher} "
            f"--offer {offer} --all --query '[].sku' -o tsv | sort -u"
        )
        raise typer.Exit(6)


# ---------------------------------------------------------------------------
# Local metadata I/O
# ---------------------------------------------------------------------------

def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(path)


def _read_credentials() -> Optional[Credentials]:
    if not CRED_FILE.exists():
        return None
    try:
        return Credentials.from_dict(json.loads(CRED_FILE.read_text()))
    except (json.JSONDecodeError, TypeError) as e:
        console.print(f"[yellow]credentials.json is corrupt:[/yellow] {e}")
        return None


def _terraform_output() -> Optional[dict]:
    """Return parsed terraform outputs, or None if no state / not applied yet."""
    tfstate = TF_DIR / "terraform.tfstate"
    if not tfstate.exists():
        return None
    try:
        result = _run(
            ["terraform", "output", "-json"],
            cwd=TF_DIR,
            capture=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return None
    raw = json.loads(result.stdout or "{}")
    if not raw:
        return None
    return {k: v["value"] for k, v in raw.items()}


# ---------------------------------------------------------------------------
# RDP file
# ---------------------------------------------------------------------------

def _write_rdp_file(creds: Credentials) -> Path:
    contents = "\r\n".join([
        f"full address:s:{creds.public_ip}",
        f"username:s:{creds.username}",
        "prompt for credentials:i:1",
        "screen mode id:i:2",
        "audiomode:i:2",
        "redirectclipboard:i:1",
        "redirectprinters:i:0",
        "drivestoredirect:s:",
    ])
    RDP_FILE.parent.mkdir(parents=True, exist_ok=True)
    RDP_FILE.write_text(contents)
    return RDP_FILE


# Microsoft's RDP client for macOS, preferred → legacy.
# In 2024 Microsoft replaced "Microsoft Remote Desktop" with the rebranded
# "Windows App" (same App Store ID), but kept the .app bundle co-installable.
RDP_APP_CANDIDATES = (
    "/Applications/Windows App.app",
    "/Applications/Microsoft Remote Desktop.app",
)


def _find_rdp_app() -> Optional[str]:
    for path in RDP_APP_CANDIDATES:
        if Path(path).exists():
            return path
    return None


def _open_rdp_file_if_possible(rdp: Path) -> None:
    app_path = _find_rdp_app()
    if app_path is None:
        console.print(
            "[yellow]Windows App / Microsoft Remote Desktop not found.[/yellow] "
            f"RDP file saved at {rdp}"
        )
        console.print(
            "  Install Windows App (formerly Microsoft Remote Desktop) from the Mac App Store: "
            "https://apps.apple.com/app/windows-app/id1295203466"
        )
        return
    try:
        # Route the .rdp file through the specific app rather than relying on
        # the system default — avoids surprises if both apps are installed.
        _run(["open", "-a", app_path, str(rdp)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]Could not auto-open RDP file:[/yellow] {e}")
        console.print(f"  File: {rdp}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def up(
    size: str = typer.Option("small", "--size", "-s", help="small | medium | large"),
    region: str = typer.Option("eastus2", "--region", "-r"),
    image_publisher: str = typer.Option("MicrosoftWindowsDesktop", "--image-publisher"),
    image_offer: str = typer.Option("windows-11", "--image-offer"),
    image_sku: str = typer.Option("win11-25h2-pro", "--image-sku"),
    shutdown_timezone: str = typer.Option(
        "Eastern Standard Time", "--shutdown-timezone",
        help="Windows-style timezone, e.g. 'Eastern Standard Time'.",
    ),
):
    """Provision a fresh ephemeral Windows VM."""
    if size not in VALID_SIZES:
        console.print(f"[red]Invalid size:[/red] {size}. Choose one of: {', '.join(VALID_SIZES)}")
        raise typer.Exit(1)

    size_map = {"small": "Standard_B2ms", "medium": "Standard_D4s_v5", "large": "Standard_D8s_v5"}
    size_sku = size_map[size]

    # Refuse if a live VM is already tracked locally.
    existing = _read_credentials()
    if existing is not None and _terraform_output() is not None:
        console.print(
            f"[red]A VM is already provisioned ({existing.run_id}, {existing.size}).[/red]"
        )
        console.print("  Run [bold]awvm status[/bold] or [bold]awvm down[/bold] first.")
        raise typer.Exit(7)

    _preflight_tools()
    sub = _preflight_azure()
    console.print(f"Using subscription: [bold]{sub.get('name')}[/bold] ({sub.get('id')})")

    _preflight_size_in_region(size_sku, region)
    _preflight_image(region, image_publisher, image_offer, image_sku)

    run_id = _generate_run_id()
    password = _generate_password()
    public_ip = _detect_public_ip()
    allowed_cidr = f"{public_ip}/32"
    username = "awvmadmin"

    console.print(f"Detected client IP: [bold]{public_ip}[/bold]")
    console.print(f"Run ID: [bold]{run_id}[/bold]  Size: [bold]{size}[/bold]  Region: [bold]{region}[/bold]")

    # terraform init (idempotent — safe to run every time).
    _run(["terraform", "init", "-input=false"], cwd=TF_DIR, check=True)

    tf_vars = [
        f"-var=run_id={run_id}",
        f"-var=size={size}",
        f"-var=region={region}",
        f"-var=allowed_cidr={allowed_cidr}",
        f"-var=admin_username={username}",
        f"-var=admin_password={password}",
        f"-var=image_publisher={image_publisher}",
        f"-var=image_offer={image_offer}",
        f"-var=image_sku={image_sku}",
        f"-var=shutdown_timezone={shutdown_timezone}",
    ]
    _run(
        ["terraform", "apply", "-auto-approve", "-input=false", *tf_vars],
        cwd=TF_DIR,
        check=True,
    )

    outputs = _terraform_output()
    if outputs is None:
        # Apply succeeded but we couldn't read outputs. Fail loud so the operator
        # knows resources exist and need manual cleanup.
        console.print(
            "[red]Apply finished but Terraform outputs are unreadable.[/red]\n"
            "  The VM likely exists. Inspect it in the Azure portal under resource group "
            f"'awvm-{run_id}-rg' and destroy with:\n"
            f"    cd terraform && terraform destroy -auto-approve {' '.join(tf_vars)}"
        )
        raise typer.Exit(8)

    creds = Credentials(
        run_id=run_id,
        size=size,
        region=region,
        rg_name=outputs["resource_group_name"],
        vm_name=outputs["vm_name"],
        nsg_name=outputs["nsg_name"],
        public_ip=outputs["public_ip"],
        username=outputs["admin_username"],
        password=password,
        allowed_cidr=allowed_cidr,
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
    )

    try:
        _atomic_write_json(CRED_FILE, creds.to_dict())
        RUN_POINTER.write_text(run_id)
    except OSError as e:
        console.print(
            f"[red]Apply succeeded but writing local metadata failed:[/red] {e}\n"
            "  VM exists. Save these credentials manually:\n"
            f"    run_id:  {run_id}\n"
            f"    rg:      {creds.rg_name}\n"
            f"    ip:      {creds.public_ip}\n"
            f"    user:    {creds.username}\n"
            f"    pass:    {creds.password}\n"
            f"  Then destroy with: cd terraform && terraform destroy -auto-approve {' '.join(tf_vars)}"
        )
        raise typer.Exit(9)

    rdp = _write_rdp_file(creds)
    _print_connect_info(creds)
    _open_rdp_file_if_possible(rdp)


def _destroy_tf_vars(creds: Optional[Credentials], tf_outputs: Optional[dict]) -> list[str]:
    """Reconstruct the `-var` args required by `terraform destroy`.

    The four variables without defaults — run_id, size, allowed_cidr,
    admin_password — must be supplied even on destroy or Terraform errors
    before it can plan the teardown. Prefer local credentials.json; fall
    back to terraform outputs for the drifted-no-creds case. For
    admin_password (sensitive, not in outputs), pass a placeholder that
    satisfies the variable — the value is unused during destroy.
    """
    if creds is not None:
        return [
            f"-var=run_id={creds.run_id}",
            f"-var=size={creds.size}",
            f"-var=allowed_cidr={creds.allowed_cidr}",
            f"-var=admin_password={creds.password}",
        ]
    outputs = tf_outputs or {}
    return [
        f"-var=run_id={outputs.get('run_id', 'drft')}",
        f"-var=size={outputs.get('size', 'small')}",
        f"-var=allowed_cidr={outputs.get('allowed_cidr', '0.0.0.0/32')}",
        # Password is sensitive and not exported; placeholder is fine on destroy.
        "-var=admin_password=Placeholder!ForDestroy0",
    ]


@app.command()
def down(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
    force_clean_local: bool = typer.Option(
        False,
        "--force-clean-local",
        help="Delete local metadata even if destroy fails. Use only after manual cloud cleanup.",
    ),
):
    """Destroy the VM and all associated resources."""
    creds = _read_credentials()
    tf_outputs = _terraform_output()

    if creds is None and tf_outputs is None:
        console.print("Nothing to destroy. No local state found.")
        return

    if not yes:
        target = creds.run_id if creds else "(unknown — tfstate only)"
        confirm = typer.confirm(f"Destroy VM {target}? This is irreversible.")
        if not confirm:
            raise typer.Exit(0)

    _preflight_tools()
    _preflight_azure()

    _run(["terraform", "init", "-input=false"], cwd=TF_DIR, check=True)

    tf_vars = _destroy_tf_vars(creds, tf_outputs)
    try:
        _run(
            ["terraform", "destroy", "-auto-approve", "-input=false", *tf_vars],
            cwd=TF_DIR,
            check=True,
        )
    except subprocess.CalledProcessError:
        console.print("[red]terraform destroy failed.[/red]")
        if creds:
            console.print(
                f"  Resources may still exist. Check the Azure portal for resource group "
                f"[bold]{creds.rg_name}[/bold] in region [bold]{creds.region}[/bold]."
            )
        if not force_clean_local:
            console.print(
                "  Local metadata preserved so you can retry. "
                "After manual cleanup, re-run with --force-clean-local to wipe it."
            )
            raise typer.Exit(10)
        console.print("[yellow]--force-clean-local set: wiping local metadata anyway.[/yellow]")

    for p in (CRED_FILE, RUN_POINTER, RDP_FILE):
        if p.exists():
            p.unlink()
    console.print("[green]Down complete.[/green]")


@app.command()
def status():
    """Show the current VM's state."""
    creds = _read_credentials()
    tf_outputs = _terraform_output()

    if creds is None and tf_outputs is None:
        console.print("State: [bold]absent[/bold] — no VM provisioned.")
        return

    if creds is None and tf_outputs is not None:
        console.print("State: [yellow]drifted[/yellow] — tfstate exists but no local metadata.")
        console.print(json.dumps(tf_outputs, indent=2))
        console.print(
            "  Recover with: [bold]awvm down --force-clean-local[/bold] after manual review."
        )
        return

    if creds is not None and tf_outputs is None:
        console.print(
            "State: [yellow]drifted[/yellow] — local metadata exists but no tfstate. "
            "VM may still exist in Azure."
        )
        console.print(json.dumps(creds.to_dict(), indent=2, default=str))
        console.print(
            f"  Check the Azure portal for resource group [bold]{creds.rg_name}[/bold]."
        )
        return

    # Both present — healthy case.
    created = dt.datetime.fromisoformat(creds.created_at)
    now = dt.datetime.now(dt.timezone.utc)
    uptime_hours = (now - created).total_seconds() / 3600.0
    rate = HOURLY_COST_USD.get(creds.size, 0.0)
    rough_spend = uptime_hours * rate

    table = Table(title=f"awvm — run {creds.run_id}", show_header=False, box=None)
    table.add_row("State", "[green]healthy[/green]")
    table.add_row("Size", creds.size)
    table.add_row("Region", creds.region)
    table.add_row("Resource group", creds.rg_name)
    table.add_row("VM name", creds.vm_name)
    table.add_row("Public IP", creds.public_ip)
    table.add_row("Allowed CIDR", creds.allowed_cidr)
    table.add_row("Username", creds.username)
    table.add_row("Created (UTC)", creds.created_at)
    table.add_row("Uptime", f"{uptime_hours:.2f} h")
    table.add_row("Approx spend", f"~${rough_spend:.2f} (planning estimate)")
    console.print(table)


@app.command()
def connect():
    """Reprint credentials and open the RDP file. No Azure API calls."""
    creds = _read_credentials()
    if creds is None:
        console.print("[red]No local credentials found.[/red] Run [bold]awvm up[/bold] first.")
        raise typer.Exit(11)
    rdp = _write_rdp_file(creds)
    _print_connect_info(creds)
    _open_rdp_file_if_possible(rdp)


@app.command()
def ip():
    """Print just the public IP of the current VM."""
    creds = _read_credentials()
    if creds is None:
        raise typer.Exit(11)
    print(creds.public_ip)


@app.command()
def rdp():
    """Regenerate the .rdp file and open it."""
    creds = _read_credentials()
    if creds is None:
        console.print("[red]No local credentials found.[/red] Run [bold]awvm up[/bold] first.")
        raise typer.Exit(11)
    path = _write_rdp_file(creds)
    _open_rdp_file_if_possible(path)
    console.print(f"RDP file: {path}")


@app.command("allow-ip-refresh")
def allow_ip_refresh():
    """Update the NSG RDP rule to the current client public IP."""
    creds = _read_credentials()
    if creds is None:
        console.print("[red]No local credentials found.[/red]")
        raise typer.Exit(11)

    _preflight_tools()
    _preflight_azure()

    new_ip = _detect_public_ip()
    new_cidr = f"{new_ip}/32"
    if new_cidr == creds.allowed_cidr:
        console.print(f"Client IP unchanged ([bold]{new_ip}[/bold]). Nothing to do.")
        return

    console.print(
        f"Updating NSG rule: [yellow]{creds.allowed_cidr}[/yellow] → "
        f"[green]{new_cidr}[/green]"
    )
    _run(
        [
            "az", "network", "nsg", "rule", "update",
            "--resource-group", creds.rg_name,
            "--nsg-name", creds.nsg_name,
            "--name", "AllowRDPFromOperator",
            "--source-address-prefixes", new_cidr,
        ],
        check=True,
    )

    creds.allowed_cidr = new_cidr
    _atomic_write_json(CRED_FILE, creds.to_dict())
    console.print("[green]NSG updated and local metadata refreshed.[/green]")


# ---------------------------------------------------------------------------
# Pretty output helpers
# ---------------------------------------------------------------------------

def _print_connect_info(creds: Credentials) -> None:
    table = Table(title=f"Windows VM {creds.run_id} is ready", show_header=False, box=None)
    table.add_row("Public IP", creds.public_ip)
    table.add_row("Username", creds.username)
    table.add_row("Password", creds.password)
    table.add_row("Region", creds.region)
    table.add_row("Size", creds.size)
    console.print(table)
    console.print(f"Credentials saved to: {CRED_FILE}")


if __name__ == "__main__":
    app()
