terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  
  backend "azurerm" {
    resource_group_name  = "terraform-state"
    storage_account_name = "terraformstate"
    container_name       = "tfstate"
    key                  = "terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-rg"
  location = var.azure_region
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-vnet"
  address_space       = [var.vpc_cidr]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  
  tags = {
    Name = "${var.project_name}-vnet"
  }
}

# Subnets
resource "azurerm_subnet" "private" {
  count = length(var.availability_zones)
  
  name                 = "${var.project_name}-private-${count.index + 1}"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.private_subnet_cidrs[count.index]]
}

resource "azurerm_subnet" "public" {
  count = length(var.availability_zones)
  
  name                 = "${var.project_name}-public-${count.index + 1}"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.public_subnet_cidrs[count.index]]
}

# Azure Database for PostgreSQL
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.project_name}-db"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "15"
  administrator_login    = var.db_username
  administrator_password = var.db_password
  zone                   = "1"
  
  sku_name = var.db_sku_name
  
  storage_mb = var.db_storage_mb
  
  backup_retention_days        = var.db_backup_retention_days
  geo_redundant_backup_enabled = var.environment == "production"
  
  maintenance_window {
    day_of_week  = 0
    start_hour   = 2
    start_minute = 0
  }
  
  tags = {
    Name = "${var.project_name}-db"
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.db_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Azure Cache for Redis
resource "azurerm_redis_cache" "main" {
  name                = "${var.project_name}-redis"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = var.redis_capacity
  family              = var.redis_family
  sku_name            = var.redis_sku_name
  
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
  
  redis_configuration {
    maxmemory_reserved = 2
    maxmemory_delta    = 2
    maxmemory_policy   = "allkeys-lru"
  }
  
  tags = {
    Name = "${var.project_name}-redis"
  }
}

# Container Instances (or AKS)
resource "azurerm_container_group" "app" {
  name                = "${var.project_name}-app"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  ip_address_type     = "Public"
  os_type             = "Linux"
  dns_name_label      = "${var.project_name}-app"
  
  container {
    name   = "app"
    image  = "${var.acr_repository_url}:${var.image_tag}"
    cpu    = "1.0"
    memory = "1.5"
    
    ports {
      port     = 5000
      protocol = "TCP"
    }
    
    environment_variables = {
      ENVIRONMENT = var.environment
      DATABASE_URL = "postgresql://${var.db_username}:${var.db_password}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${var.db_name}"
      REDIS_URL   = "redis://${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.ssl_port}?ssl=true"
    }
  }
  
  tags = {
    Name = "${var.project_name}-app"
  }
}

# Key Vault for Secrets
resource "azurerm_key_vault" "main" {
  name                = "${var.project_name}-kv"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"
  
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id
    
    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete"
    ]
  }
  
  tags = {
    Name = "${var.project_name}-kv"
  }
}

data "azurerm_client_config" "current" {}

# Application Insights
resource "azurerm_application_insights" "main" {
  name                = "${var.project_name}-insights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  
  tags = {
    Name = "${var.project_name}-insights"
  }
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  
  tags = {
    Name = "${var.project_name}-logs"
  }
}

