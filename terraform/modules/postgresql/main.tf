variable "name" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "sku_name" { type = string; default = "B_Standard_B1ms" }
variable "admin_password" { type = string; sensitive = true }
variable "delegated_subnet_id" { type = string }
variable "private_dns_zone_id" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_postgresql_flexible_server" "this" {
  name                          = var.name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  version                       = "16"
  delegated_subnet_id           = var.delegated_subnet_id
  private_dns_zone_id           = var.private_dns_zone_id
  administrator_login           = "nutriai_admin"
  administrator_password        = var.admin_password
  sku_name                      = var.sku_name
  storage_mb                    = 32768
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  public_network_access_enabled = false
  tags                          = var.tags

  lifecycle { ignore_changes = [zone] }
}

resource "azurerm_postgresql_flexible_server_database" "nutriai" {
  name      = "nutriai"
  server_id = azurerm_postgresql_flexible_server.this.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}

resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  server_id = azurerm_postgresql_flexible_server.this.id
  name      = "azure.extensions"
  value     = "UUID-OSSP"
}

output "fqdn" { value = azurerm_postgresql_flexible_server.this.fqdn }
output "connection_string" {
  value     = "postgresql://nutriai_admin:${var.admin_password}@${azurerm_postgresql_flexible_server.this.fqdn}:5432/nutriai?sslmode=require"
  sensitive = true
}
output "id" { value = azurerm_postgresql_flexible_server.this.id }
