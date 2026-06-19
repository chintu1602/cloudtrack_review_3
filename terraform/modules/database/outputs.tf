output "postgres_fqdn" {
  value       = azurerm_postgresql_flexible_server.postgres.fqdn
  description = "The fully qualified domain name of the PostgreSQL server"
}

output "postgres_id" {
  value       = azurerm_postgresql_flexible_server.postgres.id
  description = "The Resource ID of the PostgreSQL server"
}
