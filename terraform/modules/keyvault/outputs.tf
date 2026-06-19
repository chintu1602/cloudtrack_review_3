output "keyvault_id" {
  value       = azurerm_key_vault.kv.id
  description = "The Resource ID of the Azure Key Vault"
}

output "keyvault_uri" {
  value       = azurerm_key_vault.kv.vault_uri
  description = "The URI of the Azure Key Vault"
}
