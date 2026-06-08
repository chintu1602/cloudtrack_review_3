variable "name" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "app_service_plan_id" { type = string }
variable "acr_login_server" { type = string }
variable "acr_admin_username" { type = string }
variable "acr_admin_password" { type = string; sensitive = true }
variable "vnet_integration_subnet_id" { type = string }
variable "app_settings" { type = map(string); sensitive = true }
variable "tags" { type = map(string) }

resource "azurerm_linux_web_app" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = var.app_service_plan_id
  https_only          = true
  tags                = var.tags

  virtual_network_subnet_id = var.vnet_integration_subnet_id

  site_config {
    always_on                         = true
    ftps_state                        = "Disabled"
    health_check_path                 = "/health"
    container_registry_use_managed_identity = false

    application_stack {
      docker_image_name   = "nutriai-backend:latest"
      docker_registry_url = "https://${var.acr_login_server}"
      docker_registry_username = var.acr_admin_username
      docker_registry_password = var.acr_admin_password
    }
  }

  app_settings = merge(var.app_settings, {
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
    DOCKER_REGISTRY_SERVER_URL          = "https://${var.acr_login_server}"
    DOCKER_REGISTRY_SERVER_USERNAME     = var.acr_admin_username
    DOCKER_REGISTRY_SERVER_PASSWORD     = var.acr_admin_password
    WEBSITES_PORT                       = "8000"
  })

  identity { type = "SystemAssigned" }

  logs {
    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
    application_logs {
      file_system_level = "Warning"
    }
  }
}

output "id" { value = azurerm_linux_web_app.this.id }
output "default_hostname" { value = azurerm_linux_web_app.this.default_hostname }
output "principal_id" { value = azurerm_linux_web_app.this.identity[0].principal_id }
