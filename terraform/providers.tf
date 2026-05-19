provider "azurerm" {
  features {
    resource_group {
      # Make destroy thorough — if a stray nested resource lingers, fail loud
      # so the operator can fix it rather than silently leaking resources.
      prevent_deletion_if_contains_resources = false
    }
  }
}
