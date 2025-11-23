package test

import (
	"testing"
	"time"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestTerraformAwsInfrastructure(t *testing.T) {
	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../aws",
		Vars: map[string]interface{}{
			"environment":     "test",
			"project_name":    "social-media-scraper-test",
			"db_password":     "TestPassword123!",
			"ecr_repository_url": "123456789012.dkr.ecr.us-east-1.amazonaws.com/social-media-scraper",
			"image_tag":       "test",
		},
		MaxRetries:         3,
		TimeBetweenRetries: 5 * time.Second,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Test outputs
	vpcId := terraform.Output(t, terraformOptions, "vpc_id")
	assert.NotEmpty(t, vpcId)

	ecsClusterId := terraform.Output(t, terraformOptions, "ecs_cluster_id")
	assert.NotEmpty(t, ecsClusterId)

	albDnsName := terraform.Output(t, terraformOptions, "alb_dns_name")
	assert.NotEmpty(t, albDnsName)

	dbEndpoint := terraform.Output(t, terraformOptions, "db_endpoint")
	assert.NotEmpty(t, dbEndpoint)

	redisEndpoint := terraform.Output(t, terraformOptions, "redis_endpoint")
	assert.NotEmpty(t, redisEndpoint)
}

func TestTerraformGcpInfrastructure(t *testing.T) {
	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../gcp",
		Vars: map[string]interface{}{
			"gcp_project_id":  "test-project",
			"gcp_region":      "us-central1",
			"environment":     "test",
			"project_name":    "social-media-scraper-test",
			"db_password":     "TestPassword123!",
			"gcr_repository_url": "gcr.io/test-project/social-media-scraper",
			"image_tag":       "test",
		},
		MaxRetries:         3,
		TimeBetweenRetries: 5 * time.Second,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Test outputs
	vpcNetworkId := terraform.Output(t, terraformOptions, "vpc_network_id")
	assert.NotEmpty(t, vpcNetworkId)

	cloudSqlConnectionName := terraform.Output(t, terraformOptions, "cloud_sql_instance_connection_name")
	assert.NotEmpty(t, cloudSqlConnectionName)

	redisHost := terraform.Output(t, terraformOptions, "redis_host")
	assert.NotEmpty(t, redisHost)
}

func TestTerraformAzureInfrastructure(t *testing.T) {
	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../azure",
		Vars: map[string]interface{}{
			"azure_region":    "eastus",
			"environment":     "test",
			"project_name":    "social-media-scraper-test",
			"db_password":     "TestPassword123!",
			"acr_repository_url": "testregistry.azurecr.io/social-media-scraper",
			"image_tag":       "test",
		},
		MaxRetries:         3,
		TimeBetweenRetries: 5 * time.Second,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Test outputs
	resourceGroupName := terraform.Output(t, terraformOptions, "resource_group_name")
	assert.NotEmpty(t, resourceGroupName)

	postgresqlFqdn := terraform.Output(t, terraformOptions, "postgresql_fqdn")
	assert.NotEmpty(t, postgresqlFqdn)

	redisHostname := terraform.Output(t, terraformOptions, "redis_hostname")
	assert.NotEmpty(t, redisHostname)
}

