variable "resource_group_name" {
  type        = string
  description = "The name of the Resource Group"
}

variable "location" {
  type        = string
  description = "The Azure region for the ACR resource"
}

variable "acr_name" {
  type        = string
  description = "The globally unique name of the Container Registry"
}
