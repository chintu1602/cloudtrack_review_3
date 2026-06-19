resource "random_string" "storage_name" {
  length  = 12
  special = false
  upper   = false
}

resource "azurerm_storage_account" "storage" {
  name                     = "nutriai${random_string.storage_name.result}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "ZRS"
  public_network_access_enabled = false
}

resource "azurerm_storage_container" "container" {
  name                  = "nutriai-documents"
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}

# Storage Private DNS Zone
resource "azurerm_private_dns_zone" "blob_dns" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = var.resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "blob_dns_link" {
  name                  = "blob-dns-vnet-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.blob_dns.name
  virtual_network_id    = var.vnet_id
}

# Storage Private Endpoint
resource "azurerm_private_endpoint" "storage_pe" {
  name                = "storage-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.endpoints_subnet_id

  private_service_connection {
    name                           = "storage-privatelink-conn"
    private_connection_resource_id = azurerm_storage_account.storage.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "storage-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob_dns.id]
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.blob_dns_link]
}
