output "acr_id" {
  value       = azurerm_container_registry.acr.id
  description = "The Resource ID of the Container Registry"
}

output "acr_login_server" {
  value       = azurerm_container_registry.acr.login_server
  description = "The Login Server URL of the Container Registry"
}

output "acr_admin_password" {
  value       = azurerm_container_registry.acr.admin_password
  sensitive   = true
  description = "The admin login password of the Container Registry"
}

output "acr_admin_username" {
  value       = azurerm_container_registry.acr.admin_username
  description = "The admin username of the Container Registry"
}
