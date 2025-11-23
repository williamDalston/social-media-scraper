# Infrastructure Testing with Terratest

This directory contains infrastructure tests using Terratest to validate Terraform configurations.

## Prerequisites

- Go 1.19+
- Terraform installed
- Cloud provider credentials configured
- Terratest installed

## Installation

```bash
go mod init terraform-tests
go get github.com/gruntwork-io/terratest/modules/terraform
go get github.com/stretchr/testify/assert
```

## Running Tests

### AWS Tests

```bash
cd terraform/tests
go test -v -timeout 30m -run TestTerraformAwsInfrastructure
```

### GCP Tests

```bash
go test -v -timeout 30m -run TestTerraformGcpInfrastructure
```

### Azure Tests

```bash
go test -v -timeout 30m -run TestTerraformAzureInfrastructure
```

### All Tests

```bash
go test -v -timeout 30m ./...
```

## Test Structure

Tests follow this pattern:

1. **Setup**: Configure Terraform options
2. **Apply**: Run `terraform init` and `terraform apply`
3. **Validate**: Check outputs and resource existence
4. **Cleanup**: Run `terraform destroy`

## Test Coverage

- VPC/Network creation
- Database instance creation
- Redis/Cache creation
- Compute resources
- Security groups/firewall rules
- Output validation

## Best Practices

1. Use test-specific resource names
2. Set appropriate timeouts
3. Clean up resources after tests
4. Test in isolated environments
5. Validate all critical outputs

## CI/CD Integration

Add to CI/CD pipeline:

```yaml
- name: Run Infrastructure Tests
  run: |
    cd terraform/tests
    go test -v -timeout 30m ./...
```

