# Azure UI Step-by-Step Implementation Guide

This document provides a comprehensive, step-by-step guide to deploying the entire NutriAI Health Portal infrastructure via the Azure Portal UI. It also addresses image creation, building/tagging, private/public networking decisions, and SSL setup.

---

## 1. Network & Security Architecture Decisions (Public vs. Private)

To secure the application, we isolate all backend components and databases inside a Private Virtual Network (VNet), allowing only the ingress load balancer (Application Gateway) and your developer build VM to have controlled public endpoints:

| Azure Resource | Access Type | Reason for Choice |
| :--- | :--- | :--- |
| **Application Gateway Public IP** | **Public** | Must receive public browser traffic from users on HTTPS (port 443). |
| **Developer VM (Build Host)** | **Private + Bastion** | Placed on `pe-subnet` (no inbound public SSH). Outbound internet access for Docker builds is provided via its NIC public IP. SSH access is via **Azure Bastion** (no direct port 22 exposure). |
| **Container Registry (ACR)** | **Public** | Needs public endpoints (restricted via credentials) so you can push images from your build host. |
| **AKS Cluster Node Pool** | **Private** | AKS nodes run in a private subnet with no public IPs to prevent direct attacks. External ingress is handled solely by AGIC. |
| **PostgreSQL Flexible Server** | **Private** | Runs in a delegated private database subnet using **VNet Integration**. No public IP or internet access is allowed. |
| **Key Vault / Storage Account** | **Private** | Connected via **Private Endpoints** inside the Private Endpoint subnet. Public network access is disabled once keys are set. |
| **Azure OpenAI / Document Intelligence**| **Private** | Secured via **Private Endpoints** to prevent API exposure to the open web. |
| **Azure Service Bus (Premium)** | **Private** | Secured via **Private Endpoints** (Premium tier required; standard tier does not support Private Endpoints). |
| **Log Analytics / App Insights** | **Public** | Azure-managed SaaS endpoints. Traffic stays on the Microsoft backbone; no Private Endpoint required for standard telemetry. |

---

## 2. Step-by-Step Azure Portal UI Setup

### Step 2.1: Create a Resource Group
1. Search for **Resource groups** in the top search bar.
2. Click **+ Create**.
3. Select your Subscription, name the Resource Group `nutriai-rg`, and select a region (e.g., `East US`).
4. Click **Review + create** and then **Create**.

### Step 2.2: Create a VNet with 5 Subnets
1. Search for **Virtual networks** and click **+ Create**.
2. Set Resource Group: `nutriai-rg`, Name: `nutriai-vnet`, Region: `East US`.
3. Click the **IP Addresses** tab:
   * Define the VNet IP address space: `10.0.0.0/16`.
   * Click **+ Add subnet** to create the following 5 subnets:
     1. **aks-subnet**: Address range `10.0.1.0/24` (For AKS nodes).
     2. **appgw-subnet**: Address range `10.0.2.0/24` (For Azure Application Gateway).
     3. **db-subnet**: Address range `10.0.3.0/24`. Under **Subnet delegation**, select `Microsoft.DBforPostgreSQL/flexibleServers`.
     4. **pe-subnet**: Address range `10.0.4.0/24` (For Private Endpoints).
     5. **AzureBastionSubnet**: Address range `10.0.5.0/26` (For secure Bastion access, if needed).
4. Click **Review + create** and then **Create**.

---

## 3. Container Registry (ACR) & Build VM Workflow

### Step 3.1: Create Container Registry (ACR)
1. Search for **Container registries** and click **+ Create**.
2. Resource Group: `nutriai-rg`, Registry name: `nutriaiacr1602` (must be globally unique).
3. SKU: Select **Standard** (or **Premium** if you require private links for pulling).
4. Click **Review + create** and then **Create**.
5. Once created, go to the registry, click **Access keys** under settings, and check **Admin user** to enable admin credentials.

### Step 3.2: Create the Build VM (Docker Host)
1. Search for **Virtual machines** and click **+ Create** ➔ **Azure virtual machine**.
2. Name: `nutriai-build-vm`, Region: `East US`, Size: `Standard_D2s_v3` (2 vCPUs, 8GB RAM).
3. Administrator account: Select **Password**, username `azureuser`, and set password `SecureVMPassword123!`.
4. Inbound port rules: Select **None** — SSH access is via Azure Bastion, not a direct public port.
5. In the **Networking** tab:
   * Virtual Network: `nutriai-vnet`, Subnet: `pe-subnet`.
   * Public IP: **Create a new one** (needed for outbound internet access to push to ACR / install packages). This is an *outbound-only* IP — inbound SSH will be blocked.
6. Click **Review + create** and then **Create**.

> **Connecting to the VM:** Do **not** SSH directly via the VM's public IP. Use **Azure Bastion** instead — see Step 6.2 below.

### Step 3.3: Push Docker Compose Images to ACR from the VM
1. Connect to the VM via **Azure Bastion** (see Step 6.2) — do **not** SSH directly via public IP.
2. Update packages and install Docker and Docker Compose:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose
   sudo usermod -aG docker azureuser
   # Log out and log back in to apply docker group permissions
   exit
   # Reconnect via Bastion again
   ```
3. Clone your code repository containing the microservices and root `docker-compose.yml` to the VM.
4. Authenticate the VM to your ACR:
   ```bash
   docker login nutriaiacr1602.azurecr.io -u nutriaiacr1602 -p <ACR-ADMIN-PASSWORD>
   ```
5. Build the containers using Docker Compose:
   ```bash
   # Rebuild the docker compose stack locally
   docker-compose build
   ```
6. Tag the built images for the ACR and push them:
   ```bash
   # Tag and push api-gateway
   docker tag api-gateway:latest nutriaiacr1602.azurecr.io/api-gateway:latest
   docker push nutriaiacr1602.azurecr.io/api-gateway:latest

   # Tag and push auth-service
   docker tag auth-service:latest nutriaiacr1602.azurecr.io/auth-service:latest
   docker push nutriaiacr1602.azurecr.io/auth-service:latest

   # Tag and push document-service
   docker tag document-service:latest nutriaiacr1602.azurecr.io/document-service:latest
   docker push nutriaiacr1602.azurecr.io/document-service:latest

   # Tag and push diet-service
   docker tag diet-service:latest nutriaiacr1602.azurecr.io/diet-service:latest
   docker push nutriaiacr1602.azurecr.io/diet-service:latest

   # Repeat tagging and pushing for all remaining services:
   # health-service, notification-service, profile-service, admin-service, and frontend.
   ```

---

## 4. Managed Databases & Cloud Integrations

### Step 4.1: Create PostgreSQL Flexible Server (Private VNet Integration)
1. Search for **Azure Database for PostgreSQL flexible servers** and click **+ Create**.
2. Server name: `nutriai-postgres-srv`.
3. Compute + storage: Click **Configure server**:
   * Set Compute tier to **General Purpose** (e.g. `Standard_D2s_v3`). High Availability is not supported on the Burstable tier.
   * Under **High availability**, check **Enable high availability** and set the availability mode to **Zone-redundant**.
4. Authentication: Set Username (`nutriai_user`) and Password (`SecurePostgresPassword123!`).
5. In the **Networking** tab:
   * Select **Private access (VNet Integration)**.
   * Virtual network: `nutriai-vnet`.
   * Subnet: `db-subnet` (delegated to PostgreSQL).
6. Click **Review + create** and then **Create**.

### Step 4.2: Create Storage Account with Private Endpoint
1. Search for **Storage accounts** and click **+ Create**.
2. Name: `nutriaistorage` (globally unique).
3. Performance: **Standard**, Redundancy: Select **Zone-redundant storage (ZRS)**.
3. Once created, go to the storage account, click **Networking** under Security + networking:
   * Under **Firewalls and virtual networks**, select **Disabled** (or Enabled from selected VNets) to disable public access.
   * Click the **Private endpoint connections** tab, and click **+ Private endpoint**:
     * Target sub-resource: `blob`.
     * Virtual network: `nutriai-vnet`, Subnet: `pe-subnet`.
     * Create/Integrate with a Private DNS Zone: `privatelink.blob.core.windows.net`.

### Step 4.3: Create Service Bus (Premium) with Private Endpoint
1. Search for **Service Bus** and click **+ Create**.
2. Namespace name: `nutriai-bus-ns`, Pricing Tier: **Premium** (Required for private link support).
3. Once created:
   * Under settings, click **Networking** and set Public access to **Disabled**.
   * Under **Private endpoint connections**, click **+ Private endpoint**:
     * Target sub-resource: `namespace`.
     * Virtual network: `nutriai-vnet`, Subnet: `pe-subnet`.
     * Integrate with Private DNS Zone: `privatelink.servicebus.windows.net`.
   * Under **Entities** ➔ **Topics**, click **+ Topic** and create topic `meal-reminders`.
   * Under the topic `meal-reminders` ➔ **Subscriptions**, click **+ Subscription** and create subscription `email-sender`.

### Step 4.4: Create Document Intelligence & Azure OpenAI (Azure AI Foundry / Microsoft Foundry)
1. **Document Intelligence:**
   * Search for **Document Intelligence** (under AI services) and click **+ Create**.
   * Name: `nutriai-doc-intelligence`, Pricing Tier: `S0`.
   * Go to **Networking** ➔ Set Public access to **Disabled**.
   * Add a **Private Endpoint**: Target `cognitiveservices`, Subnet `pe-subnet`, DNS Zone `privatelink.cognitiveservices.azure.com`.
2. **Azure OpenAI via Azure AI Foundry / Microsoft Foundry:**
   * Search for **Azure OpenAI** and click **+ Create**.
   * Name: `nutriai-openai-service`, Pricing Tier: `S0`.
   * Deploy the model inside the **Azure AI Foundry Portal / Azure AI Studio** (ai.azure.com):
     * Model Name: `gpt-5.1` (version `2025-11-13` or newer).
     * Deployment Name: `gpt-5.1` (this deployment name matches what is used in the app configuration and the Terraform script).
   * Go to **Networking** on the Azure OpenAI resource ➔ Set Public access to **Disabled**.
   * Add a **Private Endpoint**: Target `cognitiveservices`, Subnet `pe-subnet`, DNS Zone `privatelink.cognitiveservices.azure.com`.

---

## 5. Key Vault Setup (Temporary Public to Private Transition)

To securely upload secrets before cutting off public internet access:
1. Search for **Key vaults** and click **+ Create**.
2. Name: `nutriai-kv-1602`, Access configuration: Select **Azure role-based access control (Azure RBAC)**.
3. Click **Review + create** and **Create**.
4. **Role Assignment for your User Account:**
   * Go to the Key Vault, click **Access control (IAM)** ➔ **+ Add role assignment**.
   * Select Role: **Key Vault Secrets Officer** (allows creating/reading secrets).
   * Assign access to: Your active Microsoft Entra user account. Click **Review + assign**.
5. **Upload Secrets:**
   * Go to the Key Vault ➔ **Secrets** ➔ Click **Generate/Import**.
   * Upload all environment variable secrets (replace placeholders with actual credentials):
     * Name: `database-url` ➔ Value: `postgresql://nutriai_user:nutriai_password@nutriai-postgres.postgres.database.azure.com:5432/nutriai`
     * Name: `jwt-secret-key` ➔ Value: `super-secret-jwt-key`
     * Name: `azure-storage-connection-string` ➔ Value: `<your-storage-connection-string>`
     * Name: `azure-document-intelligence-endpoint` ➔ Value: `<document-intelligence-endpoint>`
     * Name: `azure-document-intelligence-key` ➔ Value: `<document-intelligence-key>`
     * Name: `azure-openai-endpoint` ➔ Value: `<openai-endpoint>`
     * Name: `azure-openai-key` ➔ Value: `<openai-key>`
     * Name: `azure-service-bus-connection-string` ➔ Value: `<service-bus-connection-string>`
     * Name: `smtp-username` ➔ Value: `20211cst0039@gmail.com`
     * Name: `smtp-password` ➔ Value: `wnkbmlgmpryzljqi`
     * Name: `entra-client-id` ➔ Value: `<entra-client-id>`
     * Name: `entra-client-secret` ➔ Value: `<entra-client-secret>`
     * Name: `entra-tenant-id` ➔ Value: `<entra-tenant-id>`
     * Name: `applicationinsights-connection-string` ➔ Value: *(copy from Application Insights resource → Overview → Connection String)*
6. **Restrict Key Vault Access:**
   * In the Key Vault, click **Networking** under settings.
   * Change Public Access from "Allow access from all networks" to **Disable public access**.
   * Under **Private endpoint connections**, click **+ Private endpoint**:
     * Target sub-resource: `vault`.
     * Virtual network: `nutriai-vnet`, Subnet: `pe-subnet`.
     * Integrate with Private DNS Zone: `privatelink.vaultcore.azure.net`.

---

## 6. AKS & Application Gateway (AGIC) Ingress Configuration

### Step 6.1: Create AKS Cluster with AGIC, ACR & CSI Driver
1. Search for **Kubernetes services** and click **+ Create** ➔ **Create a Kubernetes cluster**.
2. Resource Group: `nutriai-rg`, Cluster name: `nutriai-aks`.
3. In the **Node pools** tab: Size `Standard_D2s_v3`, Node count `2`.
4. In the **Access** tab:
   * Under **Container Registry**, click **Attach container registry** and select `nutriaiacr1602`.
   * This automatically grants the AKS kubelet identity the **AcrPull** role on the registry.
5. In the **Networking** tab:
   * Network configuration: Select **Azure CNI (Node positions)**.
   * Virtual network: `nutriai-vnet`, Subnet: `aks-subnet`.
   * Check **Enable application gateway ingress controller (AGIC)**:
     * This will automatically create an Azure Application Gateway inside `appgw-subnet` with a Public IP address.
6. In the **Integrations** tab:
   * Under **Azure Key Vault secret provider**, check **Enable secret store CSI driver**.
   * This installs the `secrets-store.csi.k8s.io` add-on required for all `SecretProviderClass` mounts.
7. Click **Review + create** and then **Create**.

### Step 6.2: Create Azure Bastion Host (Secure VM Access)

> **Why Bastion?** The build VM sits on the private `pe-subnet` with no open SSH port. Azure Bastion provides browser-based SSH access without exposing port 22 to the internet.

1. Search for **Bastions** and click **+ Create**.
2. Resource Group: `nutriai-rg`, Name: `nutriai-bastion`, Region: `East US`.
3. Under **Virtual network**, select `nutriai-vnet`.
4. The **Subnet** field will auto-select `AzureBastionSubnet` (address range `10.0.5.0/26`).
5. Under **Public IP address**, click **Create new** → Name: `nutriai-bastion-pip`, SKU: **Standard**.
6. Click **Review + create** → **Create** *(provisioning takes ~5 minutes)*.

**To SSH into the build VM via Bastion:**
1. Navigate to the `nutriai-build-vm` resource.
2. Click **Connect** ➔ **Bastion**.
3. Enter username `azureuser` and your VM password `SecureVMPassword123!`.
4. Click **Connect** — a browser terminal opens with a shell on the VM.

### Step 6.3: Configure Managed Identity Permissions for Key Vault
1. Once AKS is created, search for **Managed Identities** in the top search bar.
2. Locate the **AKS Agent Pool Managed Identity** (usually named `nutriai-aks-agentpool` or located in the auto-generated node resource group starting with `MC_`).
3. Click **Access control (IAM)** on your Key Vault `nutriai-kv-1602` ➔ **+ Add role assignment**:
   * Select Role: **Key Vault Secrets User** (allows reading secrets).
   * Assign access to: **Managed Identity** ➔ Select the AKS Agent Pool Identity.
   * Click **Review + assign**.

### Step 6.4: Add HTTPS and Upload SSL Certificate directly to App Gateway
1. Search for **Application gateways** and select the gateway created by AGIC (e.g. `ingress-appgw`).
2. **Configure Frontend Listener for HTTPS (Port 443):**
   * Under settings, click **Listeners** ➔ **+ Add listener**.
   * Listener name: `https-listener`.
   * Frontend IP: Select **Public**.
   * Protocol: Select **HTTPS**, Port: `443`.
   * **HTTPS Certificate (Direct Upload):**
     * Under **Certificates**, select **Upload a certificate**.
     * Choose your `.pfx` SSL certificate file (containing your private key and certificate chain).
     * Name the certificate `nutriai-ssl-cert` and input the password for the `.pfx` file.
   * Click **Add**.
3. **Configure Backend Rules:**
   * Go to **Rules**, select your active routing rule (e.g. `routing-rule`), and update the target to bind the new HTTPS listener to the backend pool.
4. Save the changes.

### Step 6.5: Enable Managed Prometheus and Managed Grafana
1. Navigate to your AKS Cluster (`nutriai-aks`) in the Azure Portal.
2. Under the **Monitoring** section in the left-hand navigation pane, select **Prometheus and Grafana**.
3. Under the **Prometheus** settings:
   * Check **Enable Prometheus metrics**.
   * Under **Azure Monitor workspace**, select **Create new** (or select your existing workspace, e.g., `nutriai-prometheus-workspace`).
4. Under the **Grafana** settings:
   * Check **Link Grafana workspace**.
   * Select **Create new** (or select your existing instance, e.g., `nutriai-grafana`). Set the SKU to **Standard** and leave Managed Identity as **System Assigned**.
5. Click **Apply** or **Save** at the top. Azure will automatically provision the resources, set up the required role assignments (such as *Monitoring Data Reader* for Grafana), and configure metrics scraping endpoints on your cluster.

### Step 6.6: Create Log Analytics Workspace & Application Insights

> **Note:** If you ran Terraform, this is already provisioned automatically (`nutriai-log-analytics` + `nutriai-appinsights`). Follow this step only for a manual/portal-based setup.

#### 6.6.1 — Create Log Analytics Workspace
1. Search for **Log Analytics workspaces** and click **+ Create**.
2. Resource Group: `nutriai-rg`, Name: `nutriai-log-analytics`, Region: `East US`.
3. Under **Pricing tier**, select **Pay-as-you-go (Per GB)**. Set **Data retention** to `30` days.
4. Click **Review + create** → **Create**.

#### 6.6.2 — Create Application Insights
1. Search for **Application Insights** and click **+ Create**.
2. Resource Group: `nutriai-rg`, Name: `nutriai-appinsights`, Region: `East US`.
3. **Resource Mode**: Select **Workspace-based** *(recommended — required for new resources)*.
4. **Log Analytics Workspace**: Select `nutriai-log-analytics` (created above).
5. Click **Review + create** → **Create**.

#### 6.6.3 — Copy Connection String into Key Vault
1. Open `nutriai-appinsights` → **Overview** tab.
2. Copy the **Connection String** (e.g. `InstrumentationKey=...;IngestionEndpoint=...`).
3. Go to Key Vault `nutriai-kv-1602` → **Secrets** → **Generate/Import**.
4. Name: `applicationinsights-connection-string`, Value: *(paste the connection string)*.
5. Click **Create**.

#### 6.6.4 — View Live Telemetry
Once the application is deployed and pods are running, open `nutriai-appinsights` → **Live Metrics** to see real-time request rates, failure rates, and server telemetry from all microservices.

---

## 7. Deploying the Application

### Step 7.1: Connect to AKS Cluster
1. From your local command line (or Azure Cloud Shell), authenticate to the AKS cluster:
   ```bash
   az aks get-credentials --resource-group nutriai-rg --name nutriai-aks
   ```

### Step 7.2: Update configurations in manifests
1. Open `manifests/secret-provider.yaml` and update the parameters in each of the 8 `SecretProviderClass` objects to reference your actual Azure credentials:
   ```yaml
    userAssignedIdentityID: "<client-id-of-aks-agentpool-managed-identity>"
    keyvaultName: "nutriai-kv-1602"
    tenantId: "<your-azure-tenant-id>"
   ```

### Step 7.3: Deploy Manifests
1. Deploy namespaces, secret providers, network policies, and service deployments:
   ```bash
   kubectl apply -f manifests/namespace.yaml
   kubectl apply -f manifests/secret-provider.yaml
   kubectl apply -f manifests/network-policies.yaml
   kubectl apply -f manifests/
   ```
2. Verify that all pods are running and the secrets are mounted successfully:
   ```bash
   kubectl get pods -n nutriai
   kubectl get secrets -n nutriai
   ```
3. Get the public IP address of the Application Gateway:
   ```bash
   kubectl get ingress -n nutriai
   ```
4. Access your portal securely via `https://<YOUR-APP-GATEWAY-PUBLIC-IP>` (or map the IP to your DNS domain name).

---

## 8. Appendix: Bootstrapping Terraform Remote State & Deploying

If you choose to provision your infrastructure using the Terraform scripts instead of the manual UI clicks:

### Step 8.1: Create Storage Account for Remote State (Bootstrap)
Terraform needs an existing Storage Account to save its `terraform.tfstate` file before you run `terraform init`.
Run these Azure CLI commands to create it:
```bash
# Create the Resource Group
az group create --name nutriai-rg --location eastus

# Create a globally unique Storage Account
az storage account create \
  --name nutriaisttfstate \
  --resource-group nutriai-rg \
  --location eastus \
  --sku Standard_LRS \
  --encryption-services blob

# Create the Blob Container for the state file
az storage container create \
  --name tfstate \
  --account-name nutriaisttfstate
```

### Step 8.2: Run Terraform to Provision the Infrastructure
1. Navigate to the `terraform/` directory:
   ```bash
   cd terraform
   ```
2. Initialize Terraform (this downloads the providers and connects to your remote state in the `nutriaisttfstate` storage account):
   ```bash
   terraform init
   ```
3. Run the Terraform deployment:
   ```bash
   terraform apply
   ```
   *Terraform will automatically provision all Azure resources, securely write application secrets to the Key Vault, and configure access controls.*
---

## 9. Complete End-to-End: Run the Application with Terraform
This section is the **single runbook** to go from a blank Azure subscription to a fully running NutriAI application using Terraform. Follow steps 9.1 → 9.10 in order.

---

### Step 9.1: Install Required Tools

Make sure all tools are installed on your local machine before starting:

```bash
# 1. Azure CLI
az --version          # Need 2.50+

# 2. Terraform
terraform --version   # Need 1.5+

# 3. kubectl
kubectl version --client  # Need 1.27+

# 4. Docker (for building images on the build VM)
docker --version
```

Install links:
- Azure CLI: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
- Terraform: https://developer.hashicorp.com/terraform/install
- kubectl: https://kubernetes.io/docs/tasks/tools/

---

### Step 9.2: Authenticate to Azure

```bash
# Login to your Azure account
az login

# Confirm the correct subscription is selected
az account show

# If you need to switch subscriptions:
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
```

---

### Step 9.3: Bootstrap the Terraform Remote State Storage

Terraform stores its state remotely in a Storage Account. Run these **one-time** commands before the first `terraform init`:

```bash
# Create the Resource Group
az group create --name nutriai-rg --location eastus

# Create a globally unique Storage Account for Terraform state
az storage account create \
  --name nutriaisttfstate \
  --resource-group nutriai-rg \
  --location eastus \
  --sku Standard_LRS \
  --encryption-services blob

# Create the state container
az storage container create \
  --name tfstate \
  --account-name nutriaisttfstate
```

---

### Step 9.4: Configure `terraform.tfvars`

Copy the example configuration file `terraform.tfvars.example` to `terraform.tfvars`:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Open `terraform/terraform.tfvars` and fill in your real values before running any Terraform commands:

```hcl
resource_group_name     = "nutriai-rg"
location                = "East US"
vnet_cidr               = "10.0.0.0/16"

# PostgreSQL credentials
postgres_admin_user     = "nutriai_user"
postgres_admin_password = "SecurePostgresPassword123!"   # Change this

# Build VM credentials
vm_size                 = "Standard_D2s_v3"
vm_admin_password       = "SecureVMPassword123!"          # Change this

# Azure Key Vault
keyvault_name           = "nutriai-kv-1602"
keyvault_public_network_access_enabled = true             # Keep true for initial apply

# Container Registry
acr_name                = "nutriaiacr1602"

# AKS
aks_cluster_name        = "nutriai-aks"

# SMTP (Gmail App Password)
smtp_username           = "20211cst0039@gmail.com"
smtp_password           = "wnkb mlgm pryz ljqi"          # Gmail app password
```

> **Security Note:** Never commit real passwords to git. Use `terraform.tfvars` in `.gitignore`.

---

### Step 9.5: Initialize and Apply Terraform

```bash
cd terraform

# Download all providers (azurerm, azuread, random) and official modules (AKS, VNet, Compute)
terraform init

# Preview what will be created — review carefully
terraform plan

# Deploy all infrastructure (~15–25 minutes)
terraform apply
```

When prompted `Do you want to perform these actions?` — type `yes` and press Enter.

Terraform will provision all of the following in one command:
- ✅ Resource Group, VNet (5 subnets)
- ✅ Container Registry (`nutriaiacr1602`)
- ✅ Key Vault with Private Endpoint
- ✅ PostgreSQL Flexible Server (Zone-Redundant HA)
- ✅ Blob Storage with Private Endpoint
- ✅ Azure OpenAI (with deployed gpt-5.1 model via Azure AI Foundry / Microsoft Foundry) + Document Intelligence + Service Bus
- ✅ AKS cluster (2 nodes, AGIC, CSI driver, ACR attached)
- ✅ Entra ID App Registration + Service Principal
- ✅ Azure Bastion + Public IP
- ✅ Prometheus Workspace + Grafana + DCR
- ✅ Log Analytics Workspace + Application Insights
- ✅ All 12 Key Vault secrets (auto-written)

---

### Step 9.6: Read Terraform Outputs

After `terraform apply` completes, collect the output values — you will need them for the next steps:

```bash
# Show all outputs at once
terraform output

# Or read specific ones:
terraform output aks_kubelet_identity_client_id   # → paste into secret-provider.yaml
terraform output entra_tenant_id                  # → paste into secret-provider.yaml
terraform output acr_login_server                 # → nutriaiacr1602.azurecr.io
terraform output postgres_fqdn                    # → for DATABASE_URL verification
terraform output grafana_url                      # → Grafana dashboard URL
terraform output bastion_public_ip                # → for Bastion host IP info
```

Save these values — they are referenced in the following steps.

---

### Step 9.7: Build and Push Docker Images to ACR

Connect to the build VM via **Azure Bastion** (Step 6.2) and run:

```bash
# Authenticate Docker to ACR
docker login nutriaiacr1602.azurecr.io \
  -u nutriaiacr1602 \
  -p <ACR-ADMIN-PASSWORD>

# Get the ACR admin password from the portal or via CLI:
# az acr credential show --name nutriaiacr1602 --query passwords[0].value

# Clone your project repository
git clone https://github.com/<YOUR_REPO>/cloud_project.git
cd cloud_project

# Build all services with Docker Compose
docker-compose build

# Tag and push all service images to ACR
for service in api-gateway auth-service document-service diet-service health-service notification-service profile-service admin-service frontend; do
  docker tag ${service}:latest nutriaiacr1602.azurecr.io/${service}:latest
  docker push nutriaiacr1602.azurecr.io/${service}:latest
done

echo "All images pushed successfully."
```

---

### Step 9.8: Update Manifests with Terraform Outputs

Open `manifests/secret-provider.yaml` and replace the placeholder values in **all 8** `SecretProviderClass` definitions with the real values from Step 9.6:

```yaml
# Replace in every SecretProviderClass block:
userAssignedIdentityID: "<VALUE OF: terraform output aks_kubelet_identity_client_id>"
keyvaultName: "nutriai-kv-1602"
tenantId: "<VALUE OF: terraform output entra_tenant_id>"
```

Also, update `manifests/diet-service.yaml` to fill in the dynamic OpenAI model deployment name and API version:

```yaml
# Replace in diet-service.yaml env block:
AZURE_OPENAI_DEPLOYMENT_NAME: "<VALUE OF: terraform output openai_deployment_name>"
AZURE_OPENAI_API_VERSION: "<VALUE OF: terraform output openai_api_version>"
```

**Quick sed command to automate both files (run from project root on Linux/macOS, or edit manually on Windows/PowerShell):**
```bash
# Retrieve outputs
KUBELET_ID=$(cd terraform && terraform output -raw aks_kubelet_identity_client_id)
TENANT_ID=$(cd terraform && terraform output -raw entra_tenant_id)
OPENAI_DEPLOYMENT=$(cd terraform && terraform output -raw openai_deployment_name)
OPENAI_API_VERSION=$(cd terraform && terraform output -raw openai_api_version)

# Update secret provider class
sed -i \
  -e "s/your-identity-client-id/${KUBELET_ID}/g" \
  -e "s/placeholder-entra-tenant-id/${TENANT_ID}/g" \
  manifests/secret-provider.yaml

# Update diet service OpenAI configuration
sed -i \
  -e "s/placeholder-openai-deployment-name/${OPENAI_DEPLOYMENT}/g" \
  -e "s/placeholder-openai-api-version/${OPENAI_API_VERSION}/g" \
  manifests/diet-service.yaml
```

---

### Step 9.9: Connect to AKS and Deploy All Manifests

```bash
# 1. Get AKS credentials (merges into your local kubeconfig)
az aks get-credentials \
  --resource-group nutriai-rg \
  --name nutriai-aks \
  --overwrite-existing

# 2. Verify connection
kubectl get nodes

# 3. Create the namespace first
kubectl apply -f manifests/namespace.yaml

# 4. Deploy all SecretProviderClass definitions (must be before pods)
kubectl apply -f manifests/secret-provider.yaml

# 5. Deploy network policies
kubectl apply -f manifests/network-policies.yaml

# 6. Deploy all services and the frontend
kubectl apply -f manifests/

# 7. Wait for all pods to reach Running state (~3–5 minutes)
kubectl get pods -n nutriai --watch
```

Expected output when healthy:
```
NAME                                    READY   STATUS    RESTARTS   AGE
api-gateway-xxxxx                       1/1     Running   0          2m
auth-service-xxxxx                      1/1     Running   0          2m
diet-service-xxxxx                      1/1     Running   0          2m
document-service-xxxxx                  1/1     Running   0          2m
frontend-xxxxx                          1/1     Running   0          2m
health-service-xxxxx                    1/1     Running   0          2m
notification-service-xxxxx              1/1     Running   0          2m
profile-service-xxxxx                   1/1     Running   0          2m
admin-service-xxxxx                     1/1     Running   0          2m
```

---

### Step 9.10: Verify and Access the Application

```bash
# Get the Application Gateway public IP (assigned by AGIC)
kubectl get ingress -n nutriai

# Or via Azure CLI:
az network public-ip list \
  --resource-group <AKS_NODE_RESOURCE_GROUP> \
  --query "[?contains(name,'appgw')].ipAddress" \
  --output table
```

Open the application in your browser:
```
http://<APP-GATEWAY-PUBLIC-IP>/          → Frontend (NutriAI portal)
http://<APP-GATEWAY-PUBLIC-IP>/api/      → API Gateway
http://<APP-GATEWAY-PUBLIC-IP>/api/docs  → FastAPI Swagger UI
http://<APP-GATEWAY-PUBLIC-IP>/admin     → Admin service
```

**Verify Key Vault secrets are mounted correctly:**
```bash
# Check that all secrets are readable inside a pod
kubectl exec -n nutriai \
  $(kubectl get pod -n nutriai -l app=api-gateway -o jsonpath='{.items[0].metadata.name}') \
  -- ls /mnt/secrets-store
```

**View Grafana monitoring dashboard:**
```bash
# Get Grafana URL from Terraform output
cd terraform && terraform output grafana_url
```

Open the URL in your browser — Grafana is pre-linked to the Prometheus workspace and will show AKS cluster and pod-level metrics.

---

### Quick Troubleshooting Reference

| Symptom | Likely Cause | Fix |
| :--- | :--- | :--- |
| Pod stuck in `ImagePullBackOff` | ACR credentials issue | Verify `attached_acr_id_map` in AKS; re-run `terraform apply` |
| Pod stuck in `CrashLoopBackOff` | Secret not found in KV | Check `kubectl describe pod` and verify `secret-provider.yaml` `tenantId` |
| Pod stuck in `Init:0/1` | CSI driver not installed | Confirm `key_vault_secrets_provider_enabled = true` in AKS module |
| `terraform apply` fails on KV secrets | KV role assignment race condition | Re-run `terraform apply` — the `depends_on` will resolve it |
| Cannot SSH to build VM | Bastion not provisioned | Verify `azurerm_bastion_host` was created; connect via Portal → VM → Connect → Bastion |
| Ingress has no IP | AGIC not ready | Wait 5 minutes; check `kubectl get ingress -n nutriai -w` |

---

## Later Step: Publishing Custom Terraform Modules to the Terraform Registry
The NutriAI project uses **6 custom local modules** located in `terraform/modules/`. Publishing them to the [Terraform Registry](https://registry.terraform.io) lets you reference them by a versioned URL (like the official `Azure/aks/azurerm` module) instead of a local path.

### Custom Modules in This Project

| Local Path | Module Purpose |
| :--- | :--- |
| `terraform/modules/container_registry` | Azure Container Registry (ACR) |
| `terraform/modules/database` | PostgreSQL Flexible Server + Private DNS |
| `terraform/modules/entra_id` | Entra ID App Registration + Service Principal |
| `terraform/modules/integration` | Service Bus, Azure OpenAI, Document Intelligence |
| `terraform/modules/keyvault` | Key Vault + Private Endpoint |
| `terraform/modules/storage` | Blob Storage Account + Private Endpoint |

---

### Prerequisites

1. A **GitHub account** with a public profile (the Terraform Registry links directly to GitHub).
2. The Terraform CLI (`terraform`) installed locally.
3. Your module code already committed and working (already done in this project).

---

### Create a GitHub Repository for Each Module

The Terraform Registry requires a **strict naming convention**:
```
terraform-<PROVIDER>-<MODULE_NAME>
```

Create one **public** GitHub repository per module:

| Module | Required GitHub Repo Name |
| :--- | :--- |
| `container_registry` | `terraform-azurerm-container-registry` |
| `database` | `terraform-azurerm-database` |
| `entra_id` | `terraform-azurerm-entra-id` |
| `integration` | `terraform-azurerm-integration` |
| `keyvault` | `terraform-azurerm-keyvault` |
| `storage` | `terraform-azurerm-storage` |

**For each module:**
1. Go to [github.com/new](https://github.com/new).
2. Name the repository using the convention above (e.g., `terraform-azurerm-keyvault`).
3. Set visibility to **Public**.
4. Click **Create repository**.

---

### Structure the Module Repository

Each module repository must follow the **standard module structure**:

```
terraform-azurerm-keyvault/
├── main.tf          # Resource definitions (copy from terraform/modules/keyvault/main.tf)
├── variables.tf     # Input variable declarations
├── outputs.tf       # Output value declarations
└── README.md        # Module documentation (required by the registry)
```

**Push the module files:**
```bash
# Example for the keyvault module
git clone https://github.com/<YOUR_GITHUB_USERNAME>/terraform-azurerm-keyvault.git
cd terraform-azurerm-keyvault

# Copy the module files from the project
cp ../cloud_project/terraform/modules/keyvault/main.tf .
cp ../cloud_project/terraform/modules/keyvault/variables.tf .
cp ../cloud_project/terraform/modules/keyvault/outputs.tf .

# Create a README.md (required)
cat > README.md << 'EOF'
# terraform-azurerm-keyvault
Terraform module to create an Azure Key Vault with a Private Endpoint and Private DNS Zone integration.

## Usage
```hcl
module "keyvault" {
  source  = "<YOUR_GITHUB_USERNAME>/keyvault/azurerm"
  version = "1.0.0"
  ...
}
```
EOF

git add .
git commit -m "Initial module release v1.0.0"
git push origin main
```

Repeat this for each of the 6 modules.

---

### Tag a Release Version

The Terraform Registry uses **Git tags** (semantic versioning) to identify module versions. You must tag at least one release before publishing.

```bash
# Inside each module repo
git tag v1.0.0
git push origin v1.0.0
```

> **Important:** The tag must follow the `vMAJOR.MINOR.PATCH` format (e.g., `v1.0.0`).

---

### Publish to the Terraform Registry

1. Go to [registry.terraform.io](https://registry.terraform.io) and click **Sign in** (top right).
2. Authorize with your **GitHub account**.
3. Click **Publish** → **Module** in the top navigation bar.
4. Select the GitHub repository you want to publish (e.g., `terraform-azurerm-keyvault`).
5. The registry will automatically detect `main.tf`, `variables.tf`, and `outputs.tf`.
6. Click **Publish module**.
7. The module is now live at:
   ```
   https://registry.terraform.io/modules/<YOUR_USERNAME>/keyvault/azurerm
   ```

Repeat for all 6 modules.

---

### Update `main.tf` to Use Registry Modules

Once published, update the `source` references in `terraform/main.tf` from local paths to registry addresses:

**Before (local path):**
```hcl
module "keyvault" {
  source = "./modules/keyvault"
  ...
}
```

**After (Terraform Registry):**
```hcl
module "keyvault" {
  source  = "<YOUR_GITHUB_USERNAME>/keyvault/azurerm"
  version = "1.0.0"
  ...
}
```

**Full updated source references:**
```hcl
module "container_registry" { source = "<YOUR_USERNAME>/container-registry/azurerm"; version = "1.0.0" }
module "database"           { source = "<YOUR_USERNAME>/database/azurerm";           version = "1.0.0" }
module "entra_id"           { source = "<YOUR_USERNAME>/entra-id/azurerm";           version = "1.0.0" }
module "integration"        { source = "<YOUR_USERNAME>/integration/azurerm";        version = "1.0.0" }
module "keyvault"           { source = "<YOUR_USERNAME>/keyvault/azurerm";           version = "1.0.0" }
module "storage"            { source = "<YOUR_USERNAME>/storage/azurerm";            version = "1.0.0" }
```

After updating, run `terraform init` again to download the modules from the registry:
```bash
cd terraform
terraform init -upgrade
terraform plan
```

---

### (Optional) Private Module Registry via HCP Terraform

If you prefer **not to make repos public**, use [HCP Terraform](https://app.terraform.io) (formerly Terraform Cloud) which provides a **private module registry**:

1. Sign up at [app.terraform.io](https://app.terraform.io) (free tier available).
2. Create an **Organization**.
3. Go to **Registry** → **Publish** → **Module**.
4. Connect your **private** GitHub repository.
5. Tag a release (`git tag v1.0.0 && git push origin v1.0.0`).
6. The module is now available privately within your organization:
   ```hcl
   module "keyvault" {
     source  = "app.terraform.io/<YOUR_ORG>/keyvault/azurerm"
     version = "1.0.0"
   }
   ```
7. Update `terraform/providers.tf` to add the HCP Terraform cloud block:
   ```hcl
   terraform {
     cloud {
       organization = "<YOUR_ORG>"
       workspaces {
         name = "nutriai-prod"
       }
     }
   }
   ```

---
