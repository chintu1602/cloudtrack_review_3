resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# --- Module 1: Networking (Official Registry Module) ---
module "vnet" {
  source              = "Azure/vnet/azurerm"
  version             = "4.1.0"
  resource_group_name = azurerm_resource_group.rg.name
  vnet_location       = azurerm_resource_group.rg.location
  vnet_name           = "nutriai-vnet"
  address_space       = [var.vnet_cidr]
  
  subnet_names        = ["aks-subnet", "appgw-subnet", "db-subnet", "pe-subnet", "AzureBastionSubnet"]
  subnet_prefixes     = [
    var.subnet_prefixes["aks"],
    var.subnet_prefixes["appgw"],
    var.subnet_prefixes["database"],
    var.subnet_prefixes["endpoints"],
    var.subnet_prefixes["bastion"]
  ]

  # Delegated Subnet setup for PostgreSQL Flexible Server
  subnet_delegation = {
    db-subnet = [
      {
        name = "postgres-delegation"
        service_delegation = {
          name    = "Microsoft.DBforPostgreSQL/flexibleServers"
          actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
        }
      }
    ]
  }
}

# --- Module 2: Container Registry (Custom Local Module) ---
module "container_registry" {
  source              = "./modules/container_registry"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  acr_name            = var.acr_name
}

# --- Module 3: Key Vault (Custom Local Module) ---
module "keyvault" {
  source                        = "./modules/keyvault"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  vnet_id                       = module.vnet.vnet_id
  endpoints_subnet_id           = module.vnet.vnet_subnets[3] # pe-subnet (index 3)
  keyvault_name                 = var.keyvault_name
  public_network_access_enabled = var.keyvault_public_network_access_enabled
}

# --- Module 4: Database (Custom Local Module) ---
module "database" {
  source                  = "./modules/database"
  resource_group_name     = azurerm_resource_group.rg.name
  location                = azurerm_resource_group.rg.location
  vnet_id                 = module.vnet.vnet_id
  database_subnet_id      = module.vnet.vnet_subnets[2] # db-subnet (index 2)
  postgres_admin_user     = var.postgres_admin_user
  postgres_admin_password = var.postgres_admin_password
}

# --- Module 5: Storage (Custom Local Module) ---
module "storage" {
  source              = "./modules/storage"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  vnet_id             = module.vnet.vnet_id
  endpoints_subnet_id = module.vnet.vnet_subnets[3] # pe-subnet (index 3)
}

# --- Module 6: Integrations (Custom Local Module) ---
module "integration" {
  source              = "./modules/integration"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  vnet_id             = module.vnet.vnet_id
  endpoints_subnet_id = module.vnet.vnet_subnets[3] # pe-subnet (index 3)
  openai_model_name    = var.openai_model_name
  openai_api_version   = var.openai_api_version
}

# --- Module 7: AKS & AGIC Ingress (Official Registry Module) ---
module "aks" {
  source                           = "Azure/aks/azurerm"
  version                          = "8.0.0"
  resource_group_name              = azurerm_resource_group.rg.name
  location                         = azurerm_resource_group.rg.location
  cluster_name                     = var.aks_cluster_name
  dns_prefix                       = "nutriaiaksdns"
  prefix                           = "nutriai"
  vnet_subnet_id                   = module.vnet.vnet_subnets[0] # aks-subnet (index 0)
  os_disk_size_gb                  = 50
  agents_size                      = "Standard_D2s_v3"
  agents_count                     = 2

  # Attach ACR so AKS kubelet gets AcrPull role automatically
  attached_acr_id_map = {
    nutriai_acr = module.container_registry.acr_id
  }

  # Enable Azure Key Vault Secrets Store CSI Driver add-on
  key_vault_secrets_provider_enabled = true

  # Enable Application Gateway Ingress Controller (AGIC)
  ingress_application_gateway_enabled   = true
  ingress_application_gateway_name      = "ingress-appgw"
  ingress_application_gateway_subnet_id = module.vnet.vnet_subnets[1] # appgw-subnet (index 1)

  # Enable Prometheus metrics scraping
  monitor_metrics = {
    annotations_allowed = ""
    labels_allowed      = ""
  }
}

# --- Module 8: Compute Build VM (Official Registry Module) ---
module "compute_vm" {
  source              = "Azure/compute/azurerm"
  version             = "5.3.0"
  resource_group_name = azurerm_resource_group.rg.name
  vm_hostname         = "nutriai-build-vm"
  vm_os_publisher     = "Canonical"
  vm_os_offer         = "0001-com-ubuntu-server-jammy"
  vm_os_sku           = "22_04-lts"
  vnet_subnet_id      = module.vnet.vnet_subnets[3] # pe-subnet (index 3)
  admin_username      = "azureuser"
  admin_password      = var.vm_admin_password
  vm_size             = var.vm_size
  enable_ssh_key      = false
}

# --- Role Assignments ---

# Get current client config for deployment authentication principal ID
data "azurerm_client_config" "current" {}

# Role 1: Assign 'Key Vault Secrets User' role to AKS Kubelet Identity on Key Vault
resource "azurerm_role_assignment" "aks_kv_access" {
  scope                = module.keyvault.keyvault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = module.aks.kubelet_identity[0].object_id
}

# Role 2: Assign 'Key Vault Secrets Officer' role to the deploying User / Service Principal
resource "azurerm_role_assignment" "deployer_kv_access" {
  scope                = module.keyvault.keyvault_id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# --- Azure Monitor: Prometheus, Grafana & Application Insights ---

resource "azurerm_monitor_workspace" "prometheus" {
  name                = "nutriai-prometheus-workspace"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

resource "azurerm_dashboard_grafana" "grafana" {
  name                = "nutriai-grafana"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Standard"
  identity {
    type = "SystemAssigned"
  }
  azure_monitor_workspace_integrations {
    monitor_workspace_id = azurerm_monitor_workspace.prometheus.id
  }
}

resource "azurerm_role_assignment" "grafana_monitoring_reader" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Monitoring Reader"
  principal_id         = azurerm_dashboard_grafana.grafana.identity[0].principal_id
}

resource "azurerm_role_assignment" "grafana_metrics_reader" {
  scope                = azurerm_monitor_workspace.prometheus.id
  role_definition_name = "Monitoring Data Reader"
  principal_id         = azurerm_dashboard_grafana.grafana.identity[0].principal_id
}

resource "azurerm_monitor_data_collection_rule" "prometheus_dcr" {
  name                = "nutriai-prometheus-dcr"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  kind                = "Linux"

  destinations {
    monitor_account {
      monitor_account_id = azurerm_monitor_workspace.prometheus.id
      name               = "PrometheusWorkspace"
    }
  }

  data_flow {
    streams      = ["Microsoft-PrometheusMetrics"]
    destinations = ["PrometheusWorkspace"]
  }

  data_sources {
    prometheus_forwarder {
      name    = "PrometheusDataSource"
      streams = ["Microsoft-PrometheusMetrics"]
    }
  }
}

resource "azurerm_monitor_data_collection_rule_association" "prometheus_dcra" {
  name                    = "nutriai-prometheus-dcra"
  target_resource_id      = module.aks.aks_id
  data_collection_rule_id = azurerm_monitor_data_collection_rule.prometheus_dcr.id
}

# Log Analytics Workspace — backing store for Application Insights
resource "azurerm_log_analytics_workspace" "law" {
  name                = "nutriai-log-analytics"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# Application Insights — APM for all microservices (workspace-based)
resource "azurerm_application_insights" "appinsights" {
  name                = "nutriai-appinsights"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  workspace_id        = azurerm_log_analytics_workspace.law.id
  application_type    = "web"
}

# --- Azure Bastion (secure SSH to build VM, no public IP on VM needed) ---

resource "azurerm_public_ip" "bastion_pip" {
  name                = "nutriai-bastion-pip"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_bastion_host" "bastion" {
  name                = "nutriai-bastion"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  ip_configuration {
    name                 = "bastion-ip-config"
    subnet_id            = module.vnet.vnet_subnets[4] # AzureBastionSubnet (index 4)
    public_ip_address_id = azurerm_public_ip.bastion_pip.id
  }
}

# --- Key Vault Secrets Provisioning ---

resource "random_string" "jwt_secret" {
  length  = 32
  special = false
}

resource "azurerm_key_vault_secret" "database_url" {
  name         = "database-url"
  value        = "postgresql://${var.postgres_admin_user}:${var.postgres_admin_password}@${module.database.postgres_fqdn}:5432/nutriai"
  key_vault_id = module.keyvault.keyvault_id

  # Ensure role assignment is active before writing secrets
  depends_on = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "jwt_secret_key" {
  name         = "jwt-secret-key"
  value        = random_string.jwt_secret.result
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

# --- Module 9: Entra ID App Registration (Custom Local Module) ---
module "entra_id" {
  source           = "./modules/entra_id"
  app_display_name = "NutriAI-App-1602"
}

resource "azurerm_key_vault_secret" "entra_client_id" {
  name         = "entra-client-id"
  value        = module.entra_id.client_id
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "entra_client_secret" {
  name         = "entra-client-secret"
  value        = module.entra_id.client_secret
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "entra_tenant_id" {
  name         = "entra-tenant-id"
  value        = module.entra_id.tenant_id
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}


resource "azurerm_key_vault_secret" "azure_storage_connection_string" {
  name         = "azure-storage-connection-string"
  value        = module.storage.primary_connection_string
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "azure_document_intelligence_endpoint" {
  name         = "azure-document-intelligence-endpoint"
  value        = module.integration.doc_intel_endpoint
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "azure_document_intelligence_key" {
  name         = "azure-document-intelligence-key"
  value        = module.integration.doc_intel_key
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "azure_openai_endpoint" {
  name         = "azure-openai-endpoint"
  value        = module.integration.openai_endpoint
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "azure_openai_key" {
  name         = "azure-openai-key"
  value        = module.integration.openai_key
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "azure_service_bus_connection_string" {
  name         = "azure-service-bus-connection-string"
  value        = module.integration.service_bus_connection_string
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "smtp_username" {
  name         = "smtp-username"
  value        = var.smtp_username
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "smtp_password" {
  name         = "smtp-password"
  value        = var.smtp_password
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}

resource "azurerm_key_vault_secret" "appinsights_connection_string" {
  name         = "applicationinsights-connection-string"
  value        = azurerm_application_insights.appinsights.connection_string
  key_vault_id = module.keyvault.keyvault_id
  depends_on   = [azurerm_role_assignment.deployer_kv_access]
}
