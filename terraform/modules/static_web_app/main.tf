variable "name" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_static_web_app" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku_tier            = "Standard"
  sku_size            = "Standard"
  tags                = var.tags
}

output "default_hostname" { value = azurerm_static_web_app.this.default_host_name }
output "api_key" { value = azurerm_static_web_app.this.api_key; sensitive = true }
output "id" { value = azurerm_static_web_app.this.id }
