locals {
  size_map = {
    small  = "Standard_B2ms"
    medium = "Standard_D4s_v5"
    large  = "Standard_D8s_v5"
  }
  vm_size = local.size_map[var.size]

  name_prefix = "awvm-${var.run_id}"

  common_tags = {
    purpose    = "ephemeral-test"
    owner      = "patrick"
    run_id     = var.run_id
    size       = var.size
    managed_by = "terraform"
  }
}
