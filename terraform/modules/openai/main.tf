variable "name" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "deployment_name" { type = string; default = "gpt-4" }
variable "tags" { type = map(string) }

resource "azurerm_cognitive_account" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "OpenAI"
  sku_name            = "S0"
  tags                = var.tags

  custom_subdomain_name = var.name
}

resource "azurerm_cognitive_deployment" "gpt4" {
  name                 = var.deployment_name
  cognitive_account_id = azurerm_cognitive_account.this.id

  model {
    format  = "OpenAI"
    name    = "gpt-4"
    version = "turbo-2024-04-09"
  }

  scale {
    type     = "Standard"
    capacity = 10
  }
}

output "endpoint" { value = azurerm_cognitive_account.this.endpoint }
output "key" { value = azurerm_cognitive_account.this.primary_access_key; sensitive = true }
output "id" { value = azurerm_cognitive_account.this.id }
