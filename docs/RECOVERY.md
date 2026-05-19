# Recovery

Procedures for when `up` or `down` half-fails. The CLI is designed to fail loud rather than hide partial state — when something breaks, you'll see what to do, but this doc is the long-form reference.

## 1. `up` failed after Terraform applied but before metadata was written

**Symptom**: CLI prints "Apply succeeded but writing local metadata failed" (or similar) and exits non-zero. Azure resources exist; `.azure-windows/credentials.json` does not.

**Recover**:

1. Copy the credentials the CLI printed (run_id, RG name, IP, username, password) somewhere safe.
2. Try a clean destroy with the same `-var` set the apply used:
   ```bash
   cd terraform
   terraform destroy -auto-approve \
     -var=run_id=<run_id> \
     -var=size=<size> \
     -var=region=<region> \
     -var=allowed_cidr=<cidr> \
     -var=admin_username=awvmadmin \
     -var=admin_password=<password>
   ```
3. If that fails, delete the resource group directly:
   ```bash
   az group delete --name awvm-<run_id>-rg --yes --no-wait
   ```

## 2. `down` failed mid-destroy

**Symptom**: `awvm down` exited with "terraform destroy failed". Some Azure resources may remain.

**Recover**:

1. List what's left in the RG:
   ```bash
   az resource list --resource-group <rg_name> -o table
   ```
2. Retry the destroy:
   ```bash
   cd terraform && terraform destroy -auto-approve
   ```
3. If destroy keeps failing on a stuck resource, nuke the RG:
   ```bash
   az group delete --name <rg_name> --yes
   ```
4. Once Azure is clean, wipe local metadata:
   ```bash
   uv run scripts/awvm.py down --yes --force-clean-local
   ```

## 3. `status` says `drifted`

Two cases:

### a. Local metadata exists, tfstate does not

The VM may still exist in Azure but Terraform has forgotten about it.

```bash
# Identify the orphan resource group from the metadata.
cat .azure-windows/credentials.json
# Delete it directly.
az group delete --name <rg_name> --yes
# Wipe local metadata.
uv run scripts/awvm.py down --yes --force-clean-local
```

### b. tfstate exists, local metadata does not

You can still destroy via plain Terraform:

```bash
cd terraform && terraform destroy -auto-approve
```

You will need to provide the same `-var` values used during apply (run_id, size, region, allowed_cidr, admin_username, admin_password) since Terraform requires them. Look them up in:

- `terraform.tfstate` (outputs section has run_id, region, etc.)
- Azure portal for the password? You can't recover it — generate a new one and pass any value; destroy doesn't care if the password is valid, only that the variable is supplied.

## 4. Home IP changed and RDP stopped working

```bash
uv run scripts/awvm.py allow-ip-refresh
```

This calls `az network nsg rule update` directly — no Terraform involvement, no VM rebuild. Updates the local metadata in place.

## 5. Auto-shutdown fired and the VM is deallocated

Two options:

- **Restart in place** (preserves the OS state):
  ```bash
  az vm start --resource-group <rg_name> --name <vm_name>
  ```
- **Tear down and recreate** (cleaner, matches the "everything ephemeral" philosophy):
  ```bash
  uv run scripts/awvm.py down --yes
  uv run scripts/awvm.py up --size <tier>
  ```

## 6. Subscription / quota errors during `up`

Preflight should catch most of these. If you hit a "QuotaExceeded" or "SkuNotAvailable" mid-apply anyway:

```bash
# Find your current quota
az vm list-usage --location eastus2 -o table

# Request a quota increase via the portal, or pick a different region:
uv run scripts/awvm.py up --size small --region eastus
```
