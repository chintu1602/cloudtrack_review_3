variable "resource_group_name" {
  type        = string
  description = "The name of the Resource Group"
}

variable "location" {
  type        = string
  description = "The Azure region"
}

variable "vnet_id" {
  type        = string
  description = "The ID of the Virtual Network for DNS link"
}

variable "endpoints_subnet_id" {
  type        = string
  description = "The ID of the subnet for Private Endpoint"
}

variable "keyvault_name" {
  type        = string
  description = "The name of the Azure Key Vault"
}

variable "public_network_access_enabled" {
  type        = bool
  description = "Enable or disable public network access to Key Vault."
}
