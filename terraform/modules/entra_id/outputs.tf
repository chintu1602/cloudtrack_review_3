output "client_id" {
  value       = azuread_application.app.client_id
  description = "The Application (client) ID of the registered app"
}

output "client_secret" {
  value       = azuread_application_password.secret.value
  sensitive   = true
  description = "The auto-generated client secret value"
}

output "tenant_id" {
  value       = data.azuread_client_config.current.tenant_id
  description = "The Azure Active Directory Tenant ID"
}

output "object_id" {
  value       = azuread_application.app.object_id
  description = "The Object ID of the App Registration"
}
