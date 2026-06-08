# ============================================================
# Root Variables
# ============================================================

variable "project_name" {
  type        = string
  default     = "nutriai"
  description = "Project name prefix for all resources"
}

variable "environment" {
  type        = string
  default     = "prod"
  description = "Environment name (dev, staging, prod)"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "location" {
  type        = string
  default     = "eastus"
  description = "Azure region for all resources"
}

variable "admin_email" {
  type        = string
  description = "Admin email for alerts and notifications"
}

variable "entra_client_id" {
  type        = string
  description = "Microsoft Entra ID client ID"
  default     = ""
}

variable "entra_client_secret" {
  type        = string
  description = "Microsoft Entra ID client secret"
  sensitive   = true
  default     = ""
}

variable "entra_tenant_id" {
  type        = string
  description = "Microsoft Entra ID tenant ID"
  default     = ""
}

variable "openai_model_deployment" {
  type        = string
  default     = "gpt-4"
  description = "Azure OpenAI model deployment name"
}

variable "smtp_host" {
  type    = string
  default = "smtp.gmail.com"
}

variable "smtp_port" {
  type    = number
  default = 587
}

variable "smtp_username" {
  type      = string
  default   = ""
  sensitive = true
}

variable "smtp_password" {
  type      = string
  default   = ""
  sensitive = true
}

variable "app_service_sku" {
  type    = string
  default = "B2"
}

variable "postgres_sku" {
  type    = string
  default = "B_Standard_B1ms"
}

variable "tags" {
  type = map(string)
  default = {
    Project     = "NutriAI"
    ManagedBy   = "Terraform"
    Application = "NutriAI Health Portal"
  }
}
