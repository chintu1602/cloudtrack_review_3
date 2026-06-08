variable "name" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "container_name" { type = string; default = "nutriai-documents" }
variable "tags" { type = map(string) }

resource "azurerm_storage_account" "this" {
  name                     = replace(var.name, "-", "")
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = var.tags

  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET", "PUT", "POST", "DELETE"]
      allowed_origins    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }
  }
}

resource "azurerm_storage_container" "documents" {
  name                  = var.container_name
  storage_account_name  = azurerm_storage_account.this.name
  container_access_type = "private"
}

output "account_name" { value = azurerm_storage_account.this.name }
output "primary_access_key" { value = azurerm_storage_account.this.primary_access_key; sensitive = true }
output "connection_string" { value = azurerm_storage_account.this.primary_connection_string; sensitive = true }
output "id" { value = azurerm_storage_account.this.id }
