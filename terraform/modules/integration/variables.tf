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

variable "openai_model_name" {
  type        = string
  description = "The name/deployment name of the OpenAI model to deploy"
}

variable "openai_api_version" {
  type        = string
  description = "The API version for the OpenAI service"
}

variable "openai_model_version" {
  type        = string
  description = "The version of the OpenAI model to deploy (e.g., turbo-2024-04-09)"
}



