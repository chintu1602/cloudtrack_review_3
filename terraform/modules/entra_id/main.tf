# Get the current caller's context (tenant + object ID for ownership)
data "azuread_client_config" "current" {}

# --- App Registration ---
resource "azuread_application" "app" {
  display_name     = var.app_display_name
  owners           = [data.azuread_client_config.current.object_id]
  sign_in_audience = "AzureADMyOrg"

  web {
    redirect_uris = var.redirect_uris

    implicit_grant {
      access_token_issuance_enabled = false
      id_token_issuance_enabled     = true
    }
  }

  # Microsoft Graph — User.Read delegated permission
  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000"

    resource_access {
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d" # User.Read
      type = "Scope"
    }
  }
}

# --- Service Principal ---
resource "azuread_service_principal" "sp" {
  client_id                    = azuread_application.app.client_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id]
}

# --- Client Secret (password) ---
resource "azuread_application_password" "secret" {
  application_id = azuread_application.app.id
  display_name   = "${var.app_display_name} Secret"
  end_date       = var.secret_end_date
}
