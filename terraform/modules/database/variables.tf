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
  description = "The ID of the Virtual Network for DNS linking"
}

variable "database_subnet_id" {
  type        = string
  description = "The ID of the delegated PostgreSQL subnet"
}

variable "postgres_admin_user" {
  type        = string
  description = "Administrator username for PostgreSQL"
}

variable "postgres_admin_password" {
  type        = string
  sensitive   = true
  description = "Administrator password for PostgreSQL"
}
