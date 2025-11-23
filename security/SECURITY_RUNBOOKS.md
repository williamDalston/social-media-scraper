# Security Runbooks

This document contains operational runbooks for common security scenarios.

## Runbook: Account Lockout

### Scenario
User account is locked due to multiple failed login attempts.

### Steps

1. **Verify Lockout**
   ```bash
   # Check audit logs for failed login attempts
   GET /api/auth/audit-logs?user_id={user_id}&event_type=login_failure
   ```

2. **Review Lockout Reason**
   - Check if legitimate user or attack
   - Review IP address and user agent
   - Check for account takeover indicators

3. **Unlock Account (if legitimate)**
   ```bash
   # Admin can unlock via API or database
   # Reset failed_login_attempts and locked_until fields
   ```

4. **Investigate (if suspicious)**
   - Review all login attempts
   - Check for account takeover risks
   - Consider requiring MFA

### Prevention
- Implement CAPTCHA after multiple failures
- Require MFA for high-risk logins
- Monitor for brute force patterns

---

## Runbook: Bot Detection

### Scenario
Bot detected and blocked by security system.

### Steps

1. **Review Detection**
   ```bash
   # Check security metrics
   GET /api/admin/security/metrics
   ```

2. **Analyze Bot Activity**
   - Review user agent patterns
   - Check IP address reputation
   - Analyze request patterns

3. **Take Action**
   - If legitimate bot: Add to whitelist
   - If malicious: Add to blacklist
   - If uncertain: Monitor closely

4. **Update Rules**
   - Adjust bot detection thresholds if needed
   - Update user agent patterns
   - Refine detection algorithms

### Prevention
- Implement CAPTCHA for suspicious requests
- Use rate limiting
- Monitor for bot patterns

---

## Runbook: Fraud Detection

### Scenario
Fraud patterns detected in user behavior.

### Steps

1. **Review Fraud Alert**
   ```bash
   # Check fraud detection logs
   GET /api/auth/audit-logs?event_type=fraud_detected
   ```

2. **Analyze Fraud Patterns**
   - Review user activity
   - Check for data exfiltration
   - Analyze IP and user agent patterns

3. **Take Action**
   - **High Risk**: Block user/IP immediately
   - **Medium Risk**: Require additional verification
   - **Low Risk**: Monitor and alert

4. **Investigation**
   - Review all user actions
   - Check for data access
   - Identify fraud patterns

5. **Remediation**
   - Block malicious accounts/IPs
   - Revoke compromised credentials
   - Notify affected users if needed

### Prevention
- Monitor for unusual patterns
- Implement transaction limits
- Use fraud detection algorithms

---

## Runbook: Account Takeover Risk

### Scenario
Account takeover risk detected during login.

### Steps

1. **Review Risk Assessment**
   - Check risk level and factors
   - Review login history
   - Analyze IP and user agent changes

2. **Take Action Based on Risk**
   - **High Risk**: Block login, require MFA, notify user
   - **Medium Risk**: Require MFA or additional verification
   - **Low Risk**: Log and monitor

3. **Investigation**
   - Review account activity
   - Check for unauthorized access
   - Verify user identity

4. **Remediation**
   - If compromised: Reset credentials, revoke sessions
   - If false positive: Adjust detection rules
   - If legitimate: Whitelist IP/user agent

### Prevention
- Require MFA for high-risk logins
- Monitor for unusual login patterns
- Implement device fingerprinting

---

## Runbook: Honeypot Access

### Scenario
Honeypot endpoint accessed (indicates scanning/attack).

### Steps

1. **Review Honeypot Access**
   ```bash
   # Check honeypot access logs
   GET /api/auth/audit-logs?event_type=honeypot_accessed
   ```

2. **Analyze Access Pattern**
   - Review IP address
   - Check user agent
   - Analyze request patterns
   - Check for other suspicious activity

3. **Take Action**
   - Add IP to blacklist
   - Increase monitoring for that IP
   - Review for other attack indicators

4. **Investigation**
   - Check for other attack attempts
   - Review all activity from that IP
   - Determine attack type

### Prevention
- Honeypots are passive detection
- Use to identify attackers early
- Combine with active blocking

---

## Runbook: Security Metrics Review

### Scenario
Regular security metrics review or alert investigation.

### Steps

1. **Access Security Dashboard**
   ```bash
   GET /api/admin/security/metrics?days=7
   ```

2. **Review Metrics**
   - Overall risk assessment
   - Failed login trends
   - Bot detection trends
   - Fraud detection trends
   - Account takeover risks

3. **Analyze Trends**
   - Compare to baseline
   - Identify anomalies
   - Review recommendations

4. **Take Action**
   - Address high-risk items
   - Investigate anomalies
   - Update security controls
   - Adjust thresholds if needed

### Frequency
- **Daily**: Quick review of critical metrics
- **Weekly**: Comprehensive review
- **Monthly**: Trend analysis and reporting

---

## Runbook: IP Blacklist Management

### Scenario
Need to add or remove IPs from blacklist/whitelist.

### Steps

1. **Add to Blacklist**
   ```bash
   POST /api/admin/ip/blacklist
   {
     "ip": "192.168.1.100",
     "reason": "Multiple failed login attempts"
   }
   ```

2. **Add to Whitelist**
   ```bash
   POST /api/admin/ip/whitelist
   {
     "ip": "10.0.0.0/24",
     "reason": "Office network"
   }
   ```

3. **Review Existing Entries**
   - Check audit logs for IP activity
   - Review expiration dates
   - Remove expired entries

4. **Monitor Effectiveness**
   - Check if blocking is working
   - Review false positives
   - Adjust rules as needed

---

## Runbook: Security Incident Response

### Scenario
Security incident detected (see INCIDENT_RESPONSE_PLAN.md for details).

### Quick Response Checklist

- [ ] Classify incident severity
- [ ] Notify incident response team
- [ ] Contain threat (block IPs, disable accounts)
- [ ] Preserve evidence (logs, snapshots)
- [ ] Investigate scope and impact
- [ ] Document findings
- [ ] Remediate (remove threat, patch vulnerabilities)
- [ ] Verify recovery
- [ ] Post-incident review

---

## Runbook: Security Audit

### Scenario
Regular security audit or compliance review.

### Steps

1. **Generate Compliance Report**
   ```bash
   GET /api/auth/admin/compliance/report?days=30
   ```

2. **Review Audit Logs**
   ```bash
   GET /api/auth/audit-logs?start_date={date}&end_date={date}
   ```

3. **Review Security Metrics**
   ```bash
   GET /api/admin/security/metrics?days=30
   ```

4. **Document Findings**
   - Security events summary
   - Compliance status
   - Recommendations
   - Action items

### Frequency
- **Monthly**: Internal security review
- **Quarterly**: Comprehensive audit
- **Annually**: Full compliance audit

---

## Emergency Contacts

- **Security Team**: [Contact Info]
- **On-Call Engineer**: [Contact Info]
- **Management**: [Contact Info]
- **Legal/Compliance**: [Contact Info]

---

**Last Updated**: 2024
**Next Review**: Quarterly

