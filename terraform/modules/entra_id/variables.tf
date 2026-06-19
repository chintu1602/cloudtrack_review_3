variable "app_display_name" {
  type        = string
  description = "Display name for the Entra ID App Registration"
}

variable "redirect_uris" {
  type        = list(string)
  description = "OAuth2 redirect URIs for the web application"
  default = [
    "http://localhost:8000/auth/microsoft/callback",
    "https://nutriai.example.com/auth/microsoft/callback"
  ]
}

variable "secret_end_date" {
  type        = string
  description = "Expiry date for the client secret (RFC3339)"
  default     = "2028-01-01T00:00:00Z"
}
