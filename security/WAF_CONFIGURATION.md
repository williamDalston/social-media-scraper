# Web Application Firewall (WAF) Configuration

## Overview

This document provides guidance for configuring a Web Application Firewall (WAF) for the HHS Social Media Scraper application.

## Recommended WAF Solutions

### Cloud-Based Options
1. **AWS WAF** (if using AWS)
2. **Cloudflare WAF**
3. **Azure Application Gateway WAF** (if using Azure)
4. **Google Cloud Armor** (if using GCP)

### Self-Hosted Options
1. **ModSecurity** (Apache/Nginx)
2. **NAXSI** (Nginx)
3. **OWASP ModSecurity Core Rule Set**

## WAF Rules Configuration

### 1. Rate Limiting Rules

```yaml
Rate Limiting:
  - Rule: Limit requests per IP
    Rate: 100 requests per minute
    Action: Block for 1 hour
    
  - Rule: Limit login attempts
    Rate: 5 attempts per minute per IP
    Action: Block for 30 minutes
    
  - Rule: Limit API requests
    Rate: 1000 requests per hour per user
    Action: Throttle
```

### 2. SQL Injection Protection

```yaml
SQL Injection Rules:
  - Pattern: union.*select
    Action: Block
    
  - Pattern: ';.*--
    Action: Block
    
  - Pattern: exec\(
    Action: Block
    
  - Pattern: drop.*table
    Action: Block
```

### 3. XSS Protection

```yaml
XSS Protection Rules:
  - Pattern: <script[^>]*>
    Action: Block
    
  - Pattern: javascript:
    Action: Block
    
  - Pattern: on\w+\s*=
    Action: Block
    
  - Pattern: <iframe
    Action: Block
```

### 4. Path Traversal Protection

```yaml
Path Traversal Rules:
  - Pattern: \.\./
    Action: Block
    
  - Pattern: \.\.\\
    Action: Block
    
  - Pattern: \.env
    Action: Block
    
  - Pattern: \.git
    Action: Block
```

### 5. File Upload Protection

```yaml
File Upload Rules:
  - Allowed Types: .csv only
  - Max Size: 10MB
  - Content Validation: Required
  - Virus Scanning: Recommended
```

### 6. Bot Protection

```yaml
Bot Protection:
  - User Agent Filtering: Enabled
  - CAPTCHA: After 5 failed attempts
  - Bot Detection: Enabled
  - Allow Known Bots: Configure whitelist
```

## AWS WAF Configuration Example

```json
{
  "Rules": [
    {
      "Name": "RateLimitRule",
      "Priority": 1,
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      },
      "Action": {
        "Block": {}
      }
    },
    {
      "Name": "SQLInjectionRule",
      "Priority": 2,
      "Statement": {
        "ByteMatchStatement": {
          "SearchString": "union.*select",
          "FieldToMatch": {
            "AllQueryArguments": {}
          },
          "TextTransformations": [
            {
              "Type": "LOWERCASE",
              "Priority": 0
            }
          ]
        }
      },
      "Action": {
        "Block": {}
      }
    },
    {
      "Name": "XSSRule",
      "Priority": 3,
      "Statement": {
        "ByteMatchStatement": {
          "SearchString": "<script",
          "FieldToMatch": {
            "AllQueryArguments": {}
          }
        }
      },
      "Action": {
        "Block": {}
      }
    }
  ]
}
```

## Cloudflare WAF Configuration

### Managed Rules
- Enable OWASP Core Rule Set
- Enable Cloudflare Managed Rules
- Enable Bot Fight Mode

### Custom Rules
```javascript
// Rate limiting
(http.request.uri.path eq "/api/auth/login" and 
 rate(5 per 1m) > 5) => block()

// SQL injection
(http.request.uri.query contains "union select") => block()

// XSS
(http.request.body contains "<script") => block()
```

## DDoS Protection Strategies

### 1. Rate Limiting
- Implement at multiple layers (WAF, application, database)
- Use sliding window algorithms
- Configure per-endpoint limits

### 2. IP Filtering
- Blacklist known malicious IPs
- Whitelist trusted IPs
- Use IP reputation services

### 3. Challenge-Response
- CAPTCHA for suspicious requests
- JavaScript challenges
- Proof-of-work challenges

### 4. Traffic Analysis
- Monitor traffic patterns
- Detect anomalies
- Auto-scale resources

### 5. CDN Integration
- Use CDN for static assets
- Distribute traffic geographically
- Absorb DDoS at edge

## Implementation Checklist

### WAF Setup
- [ ] Choose WAF solution
- [ ] Configure rate limiting rules
- [ ] Configure SQL injection protection
- [ ] Configure XSS protection
- [ ] Configure path traversal protection
- [ ] Configure file upload rules
- [ ] Configure bot protection
- [ ] Test WAF rules
- [ ] Monitor WAF logs
- [ ] Tune rules based on traffic

### DDoS Protection
- [ ] Configure rate limiting
- [ ] Set up IP filtering
- [ ] Implement challenge-response
- [ ] Configure traffic analysis
- [ ] Set up CDN
- [ ] Test DDoS mitigation
- [ ] Document procedures

## Monitoring and Tuning

### Metrics to Monitor
- Blocked requests count
- False positive rate
- Response time impact
- Legitimate traffic blocked
- Attack patterns detected

### Tuning Guidelines
1. Start with strict rules
2. Monitor false positives
3. Adjust rules gradually
4. Whitelist legitimate patterns
5. Review and update regularly

## Incident Response

### DDoS Attack Response
1. Activate DDoS mitigation
2. Scale resources if needed
3. Block attack sources
4. Monitor traffic patterns
5. Document attack details
6. Post-incident review

### WAF False Positive
1. Identify blocked legitimate request
2. Review WAF logs
3. Adjust rule or add exception
4. Test fix
5. Monitor for recurrence

## Best Practices

1. **Layered Defense**: Use WAF + application-level protection
2. **Regular Updates**: Keep WAF rules updated
3. **Monitoring**: Monitor WAF effectiveness
4. **Testing**: Regular security testing
5. **Documentation**: Document all rules and exceptions
6. **Review**: Regular security reviews

---

**Last Updated**: 2024
**Next Review**: Quarterly

