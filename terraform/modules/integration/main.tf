# --- Service Bus Premium ---
resource "azurerm_servicebus_namespace" "sb" {
  name                = "nutriai-bus-ns"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Premium"
  capacity            = 1
  public_network_access_enabled = false
}

resource "azurerm_servicebus_topic" "topic" {
  name         = "meal-reminders"
  namespace_id = azurerm_servicebus_namespace.sb.id
}

resource "azurerm_servicebus_subscription" "sub" {
  name               = "email-sender"
  topic_id           = azurerm_servicebus_topic.topic.id
  max_delivery_count = 10
}

resource "azurerm_servicebus_namespace_authorization_rule" "sb_rule" {
  name         = "RootManageSharedAccessKey"
  namespace_id = azurerm_servicebus_namespace.sb.id
  listen       = true
  send         = true
  manage       = true
}

# Service Bus DNS Zone
resource "azurerm_private_dns_zone" "sb_dns" {
  name                = "privatelink.servicebus.windows.net"
  resource_group_name = var.resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "sb_dns_link" {
  name                  = "sb-dns-vnet-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.sb_dns.name
  virtual_network_id    = var.vnet_id
}

# Service Bus Private Endpoint
resource "azurerm_private_endpoint" "sb_pe" {
  name                = "sb-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.endpoints_subnet_id

  private_service_connection {
    name                           = "sb-privatelink-conn"
    private_connection_resource_id = azurerm_servicebus_namespace.sb.id
    subresource_names              = ["namespace"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "sb-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.sb_dns.id]
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.sb_dns_link]
}


# --- Cognitive Services DNS Zone ---
resource "azurerm_private_dns_zone" "cog_dns" {
  name                = "privatelink.cognitiveservices.azure.com"
  resource_group_name = var.resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "cog_dns_link" {
  name                  = "cog-dns-vnet-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.cog_dns.name
  virtual_network_id    = var.vnet_id
}


# --- Azure OpenAI ---
resource "azurerm_cognitive_account" "openai" {
  name                = "nutriai-openai-service"
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "OpenAI"
  sku_name            = "S0"
  public_network_access_enabled = false
}

# OpenAI Private Endpoint
resource "azurerm_private_endpoint" "openai_pe" {
  name                = "openai-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.endpoints_subnet_id

  private_service_connection {
    name                           = "openai-privatelink-conn"
    private_connection_resource_id = azurerm_cognitive_account.openai.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "openai-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.cog_dns.id]
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.cog_dns_link]
}


# --- Document Intelligence ---
resource "azurerm_cognitive_account" "doc_intel" {
  name                = "nutriai-doc-intelligence"
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "FormRecognizer"
  sku_name            = "S0"
  public_network_access_enabled = false
}

# Document Intelligence Private Endpoint
resource "azurerm_private_endpoint" "doc_intel_pe" {
  name                = "doc-intel-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.endpoints_subnet_id

  private_service_connection {
    name                           = "doc-intel-privatelink-conn"
    private_connection_resource_id = azurerm_cognitive_account.doc_intel.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "doc-intel-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.cog_dns.id]
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.cog_dns_link]
}
