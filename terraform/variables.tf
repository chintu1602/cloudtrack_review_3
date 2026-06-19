variable "resource_group_name" {
  type        = string
  description = "Name of the resource group to contain all resources"
  default     = "nutriai-rg"
}

variable "location" {
  type        = string
  description = "Azure region where resources will be deployed"
  default     = "East US"
}

variable "vnet_cidr" {
  type        = string
  description = "CIDR block for the virtual network"
  default     = "10.0.0.0/16"
}

variable "subnet_prefixes" {
  type        = map(string)
  description = "CIDR blocks for individual subnets"
  default = {
    aks      = "10.0.1.0/24"
    appgw    = "10.0.2.0/24"
    database = "10.0.3.0/24"
    endpoints = "10.0.4.0/24"
    bastion  = "10.0.5.0/26"
  }
}

variable "postgres_admin_user" {
  type        = string
  description = "Administrator login username for PostgreSQL Flexible Server"
  default     = "nutriai_user"
}

variable "postgres_admin_password" {
  type        = string
  description = "Administrator login password for PostgreSQL Flexible Server"
  sensitive   = true
  default     = "P@ssw0rd12345!"
}

variable "vm_admin_password" {
  type        = string
  description = "Administrator password for VM authentication"
  sensitive   = true
  default     = "SecureVMPassword123!"
}

variable "vm_size" {
  type        = string
  description = "Virtual machine size for build/docker host"
  default     = "Standard_D2s_v3"
}

variable "keyvault_name" {
  type        = string
  description = "Name of the Azure Key Vault (globally unique)"
  default     = "nutriai-kv-1602"
}

variable "acr_name" {
  type        = string
  description = "Name of the Azure Container Registry (globally unique)"
  default     = "nutriaiacr1602"
}

variable "aks_cluster_name" {
  type        = string
  description = "Name of the AKS Cluster"
  default     = "nutriai-aks"
}

variable "keyvault_public_network_access_enabled" {
  type        = bool
  description = "Set to true to whitelist the deployer's IP to write secrets, set to false to lock down the Key Vault completely."
  default     = true
}


variable "smtp_username" {
  type        = string
  description = "SMTP username for sending meal reminders"
  sensitive   = true
  default     = "20211cst0039@gmail.com"
}

variable "smtp_password" {
  type        = string
  description = "SMTP App Password for Gmail"
  sensitive   = true
  default     = "wnkbmlgmpryzljqi"
}

variable "openai_model_name" {
  type        = string
  description = "The name/deployment name of the OpenAI model to deploy (e.g., gpt-4, gpt-5.1)"
  default     = "gpt-4"
}

variable "openai_api_version" {
  type        = string
  description = "The API version for the OpenAI service"
  default     = "2024-02-01"
}

variable "openai_model_version" {
  type        = string
  description = "The version of the OpenAI model to deploy (e.g., turbo-2024-04-09)"
  default     = "turbo-2024-04-09"
}



