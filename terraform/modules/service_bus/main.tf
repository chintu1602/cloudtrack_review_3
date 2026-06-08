variable "name" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "topic_name" { type = string; default = "meal-reminders" }
variable "subscription_name" { type = string; default = "email-sender" }
variable "tags" { type = map(string) }

resource "azurerm_servicebus_namespace" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_servicebus_topic" "meal_reminders" {
  name         = var.topic_name
  namespace_id = azurerm_servicebus_namespace.this.id
  max_size_in_megabytes = 1024
}

resource "azurerm_servicebus_subscription" "email_sender" {
  name               = var.subscription_name
  topic_id           = azurerm_servicebus_topic.meal_reminders.id
  max_delivery_count = 5
}

resource "azurerm_servicebus_namespace_authorization_rule" "app" {
  name         = "app-access"
  namespace_id = azurerm_servicebus_namespace.this.id
  listen       = true
  send         = true
  manage       = false
}

output "connection_string" {
  value     = azurerm_servicebus_namespace_authorization_rule.app.primary_connection_string
  sensitive = true
}
output "id" { value = azurerm_servicebus_namespace.this.id }
