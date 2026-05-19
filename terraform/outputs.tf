output "run_id" {
  description = "Short run identifier."
  value       = var.run_id
}

output "size" {
  description = "Sizing tier."
  value       = var.size
}

output "region" {
  description = "Azure region."
  value       = var.region
}

output "resource_group_name" {
  description = "Resource group containing all VM resources."
  value       = azurerm_resource_group.main.name
}

output "vm_name" {
  description = "Windows VM name."
  value       = azurerm_windows_virtual_machine.main.name
}

output "nsg_name" {
  description = "Network security group name (used by allow-ip-refresh)."
  value       = azurerm_network_security_group.main.name
}

output "public_ip" {
  description = "Public IP address for RDP."
  value       = azurerm_public_ip.main.ip_address
}

output "admin_username" {
  description = "Local Windows admin username."
  value       = var.admin_username
}

output "allowed_cidr" {
  description = "CIDR currently allowed for RDP."
  value       = var.allowed_cidr
}
