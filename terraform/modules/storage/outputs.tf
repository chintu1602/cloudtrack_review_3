output "storage_id" {
  value       = azurerm_storage_account.storage.id
  description = "The Resource ID of the Storage Account"
}

output "primary_connection_string" {
  value       = azurerm_storage_account.storage.primary_connection_string
  sensitive   = true
  description = "The primary connection string of the Storage Account"
}
