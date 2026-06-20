output "resource_group_name" {
  value       = var.resource_group_name
  description = "The name of the Resource Group"
}

output "vnet_name" {
  value       = module.vnet.vnet_name
  description = "The name of the Virtual Network"
}

output "acr_login_server" {
  value       = module.container_registry.acr_login_server
  description = "The ACR Login Server endpoint"
}

output "build_vm_public_ip" {
  value       = module.compute_vm.public_ip_address
  description = "The public IP of the developer build VM"
}

output "keyvault_uri" {
  value       = module.keyvault.keyvault_uri
  description = "The Azure Key Vault Vault URI"
}

output "postgres_fqdn" {
  value       = module.database.postgres_fqdn
  description = "The fully qualified domain name of the PostgreSQL server"
}

output "aks_node_resource_group" {
  value       = module.aks.node_resource_group
  description = "The auto-generated Resource Group containing the AKS agent resources"
}

output "app_gateway_id" {
  value       = try(module.aks.ingress_application_gateway.effective_gateway_id, null)
  description = "The Resource ID of the Application Gateway (Ingress)"
}

output "grafana_url" {
  value       = try(jsondecode(azurerm_resource_group_template_deployment.grafana.output_content).endpoint.value, "")
  description = "The URL of the Azure Managed Grafana Dashboard"
}

output "aks_kubelet_identity_client_id" {
  value       = module.aks.kubelet_identity[0].client_id
  description = "The Client ID of the AKS Kubelet Managed Identity (use as userAssignedIdentityID in secret-provider.yaml)"
}

output "entra_app_client_id" {
  value       = module.entra_id.client_id
  description = "The Application (client) ID of the NutriAI Entra ID App Registration"
}

output "entra_tenant_id" {
  value       = module.entra_id.tenant_id
  description = "The Azure Active Directory Tenant ID"
}

output "bastion_public_ip" {
  value       = azurerm_public_ip.bastion_pip.ip_address
  description = "The public IP address of the Azure Bastion host"
}

output "application_insights_name" {
  value       = azurerm_application_insights.appinsights.name
  description = "The name of the Application Insights resource"
}

output "openai_deployment_name" {
  value       = var.openai_model_name
  description = "The deployment name of the OpenAI model"
}

