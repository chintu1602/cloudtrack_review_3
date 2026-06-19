output "service_bus_connection_string" {
  value     = azurerm_servicebus_namespace_authorization_rule.sb_rule.primary_connection_string
  sensitive = true
  description = "The primary connection string of the Service Bus"
}

output "openai_endpoint" {
  value       = azurerm_cognitive_account.openai.endpoint
  description = "The endpoint URL of the Azure OpenAI service"
}

output "openai_key" {
  value     = azurerm_cognitive_account.openai.primary_access_key
  sensitive = true
  description = "The access key of the Azure OpenAI service"
}

output "doc_intel_endpoint" {
  value       = azurerm_cognitive_account.doc_intel.endpoint
  description = "The endpoint URL of the Document Intelligence service"
}

output "doc_intel_key" {
  value     = azurerm_cognitive_account.doc_intel.primary_access_key
  sensitive = true
  description = "The access key of the Document Intelligence service"
}
