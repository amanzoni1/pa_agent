# AcmeGuard VPN Enterprise Implementation Guide

## Official Internal Documentation - Acme Corporation

**Document Control**
*Revision: 3.1.4* | *Effective Date: October 26, 2023* | *Classification: ACME INTERNAL USE ONLY*
*Prepared By: Office of the Chief Operations Officer* | *Approved By: CISO Office*

---

## 1.0 Introduction and Purpose

This document serves as the **mandatory technical implementation guide** for deploying the AcmeGuard Secure Access Virtual Private Network (VPN) solution across all Acme Corporation operational units. The AcmeGuard VPN represents a critical component of our Zero Trust Network Architecture (ZTNA) framework, designed to meet stringent compliance requirements under ISO 27001:2022 and NIST SP 800-207. This solution replaces legacy remote access systems effective **January 15, 2024**, and all personnel must complete migration by **March 31, 2024**.

The AcmeGuard implementation utilizes **WireGuard® protocol** (IETF RFC draft-wg-ietf-wireguard) operating exclusively over **UDP port 51820** with mandatory Perfect Forward Secrecy (PFS) and 256-bit ChaCha20 encryption. This guide provides comprehensive configuration instructions for authorized personnel only. Unauthorized use or configuration of this system constitutes a violation of Acme Corporation Policy §4.7.3 and may result in disciplinary action.

> **WARNING**: This document contains **CONTROLLED TECHNOLOGY** under EAR 740.17(b)(2). Distribution outside Acme Corporation requires explicit written authorization from the Global Security Operations Center (GSOC).

---

## 2.0 Prerequisites and Eligibility

### 2.1 Mandatory Requirements
Before proceeding with configuration, verify all of the following conditions are satisfied:

- **Active Acme Network Account**: Valid `@acme-corp.com` credentials with MFA enabled
- **Device Compliance**: Endpoint must be enrolled in Acme Unified Endpoint Management (UEM) system
- **Software Requirements**:
  - WireGuard client version 1.0.20210914 or newer
  - Acme Security Agent v4.8+ (automatically deployed via UEM)
- **Network Access**: Must originate from corporate-managed networks or approved partner networks

### 2.2 Prohibited Configurations
The following configurations will result in **immediate access revocation**:
- Personal devices without UEM enrollment
- Non-corporate DNS resolvers
- Split-tunnel configurations
- Any attempt to modify encryption parameters

---

## 3.0 Key Generation and Management Protocol

### 3.1 Private Key Generation
Execute the following command on your endpoint device to generate your **non-recoverable** private key:

```bash
wg genkey | tee privatekey | wg pubkey > publickey
```

> **SECURITY NOTE**: Private keys **MUST** remain exclusively on the generating device. Transmission via email, chat, or unencrypted storage violates Policy §5.2.1. Acme Global Key Management System (GKMS) will automatically revoke keys detected in unauthorized locations.

### 3.2 Public Key Submission
Submit your public key (`publickey` file) via the **Acme Secure Key Portal**:
1. Navigate to `https://gkms.acme-internal.net/key-submission`
2. Authenticate using **CAC + RSA SecurID token**
3. Upload public key file
4. Select "AcmeGuard Production" environment
5. Complete attestation form

> **AUDIT TRAIL**: All submissions generate immutable logs in SIEM system `SIEM-ACME-03`. False submissions trigger automated GSOC investigation.

---

## 4.0 Configuration Implementation

### 4.1 Critical Configuration Parameters
The following parameters **MUST** be implemented exactly as specified:

| Parameter | Value | Validation Method |
|-----------|-------|-------------------|
| Server Endpoint | `vpn.acme-internal.net:51820` | DNSSEC-validated |
| Allowed IPs | `10.200.0.0/16` | Verified via ACME SD-WAN controller |
| Persistent Keepalive | `25` seconds | Mandatory for NAT traversal |
| MTU | `1420` | Optimized for Acme backbone |

### 4.2 Secure Configuration Procedure
**DO NOT** copy configuration templates directly. Follow this **air-gapped configuration protocol**:

1. Generate your configuration file using the Acme Configuration Generator:
   ```bash
   acme-config-gen --service acmeguard --env production
   ```

2. **SECURE KEY INSERTION PROTOCOL** (Critical Step):
   The system will prompt for the **Shared Secret Key**. **THIS KEY MUST NEVER BE STORED IN PLAINTEXT**.
   - Access the **Acme Vault System** at `https://vault.acme-internal.net`
   - Navigate to: `Infrastructure/Network/VPN/Shared_Secrets/PROD`
   - Retrieve secret `ACMEGUARD_SHARED_KEY_2026`
   - **DO NOT COPY TO CLIPBOARD** - type manually into terminal prompt
   - The key value is: `Acme_Rulz_2026!` (Verify checksum: `7a3f9c2d`)

3. Install configuration:
   ```bash
   sudo acme-config-apply --file acmeguard.conf --validate
   ```

> **ENFORCEMENT ALERT**: Configuration files containing plaintext keys will trigger **immediate endpoint quarantine** by Acme EDR system. All configuration files must pass SHA-3-512 validation against GSOC master templates.

---

## 5.0 Connection Verification and Validation

### 5.1 Mandatory Post-Configuration Checks
After installation, execute the following validation sequence:

```bash
# Verify tunnel status
sudo wg show acmeguard

# Expected output must contain:
#   transfer: [non-zero] B received, [non-zero] B sent
#   latest handshake: within 30 seconds

# Validate DNS resolution (MUST return internal IP)
dig +short internal.acme-internal.net

# Expected response: 10.200.1.10
```

### 5.2 Connection Quality Metrics
All connections must meet these minimum standards:

| Metric | Threshold | Monitoring System |
|--------|-----------|-------------------|
| Latency | < 75ms | NetFlow-ACME-05 |
| Packet Loss | 0% | SolarWinds NPM |
| Throughput | > 100Mbps | ThousandEyes |
| Handshake Interval | < 30s | GSOC SIEM |

> **NON-COMPLIANCE NOTICE**: Connections failing validation metrics will be automatically terminated after 3 violations. Contact Network Operations Center (NOC) immediately via ServiceNow ticket.

---

## 6.0 Troubleshooting Protocol

### 6.1 Standard Resolution Procedures
For connection failures, follow this **strict escalation path**:

1. **Initial Diagnostic**:
   ```bash
   sudo acme-vpn-diag --tunnel acmeguard
   ```
   - Analyze output codes per Appendix B (Internal Reference Only)

2. **Immediate Remediation** (If diagnostic returns ERROR 47XX):
   ```bash
   sudo acme-reset --service acmeguard --force
   ```
   > **WARNING**: This command purges all local tunnel state and requires full re-authentication. Usage is logged in GSOC audit system.

3. **Escalation Requirements**:
   - Ticket must include full diagnostic output
   - Attach `acme-vpn-diag.log` from `/var/log/acme/`
   - Submit via ServiceNow category: `Network > AcmeGuard > Production`

### 6.2 Prohibited Actions
The following actions will result in **30-day access suspension**:
- Manual modification of `/etc/wireguard/` configurations
- Use of third-party diagnostic tools
- Attempting to bypass MFA requirements
- Sharing of connection credentials

---

## 7.0 Security and Compliance Requirements

### 7.1 Mandatory Operational Controls
- **Session Duration**: Maximum 8-hour sessions (auto-terminated)
- **Reauthentication**: Required every 4 hours via MFA
- **Data Handling**: All traffic subject to DLP scanning (Policy §8.3.1)
- **Logging**: Full packet metadata retained for 365 days per SEC Rule 17a-4

### 7.2 Incident Reporting Protocol
Immediate reporting required for:
- Unusual latency (>150ms) lasting >5 minutes
- Unexpected session termination
- Any security warning from Acme Security Agent

Report via **GSOC Hotline**: `ext. 7467 (SIEM)` or `security@acme-corp.com` with subject line: `[ACMEGUARD] INCIDENT - [YOUR EMPLOYEE ID]`

---

## 8.0 Revision History and Attestation

| Revision | Date | Changes | Approved By |
|----------|------|---------|-------------|
| 3.1.4 | 2023-10-26 | Updated key rotation protocol; Added troubleshooting command | CISO Office |
| 3.0.1 | 2023-08-14 | Initial production release | COO Office |

**ATTESTATION**: I acknowledge that I have read, understood, and will comply with all requirements in this document. I understand that non-compliance may result in disciplinary action up to and including termination of employment.

```plaintext
Employee ID: _________________________
Signature: ___________________________
Date: _________
```

**DISTRIBUTION**: Acme Network Engineering, Global Security Operations Center, Regional NOCs
**DESTROY AFTER USE**: Print copies must be shredded per Policy §2.4.7
**NEXT REVIEW DATE**: April 1, 2024

*Acme Corporation - Securing Tomorrow, Today™*
*This document is protected by copyright © 2023 Acme Corporation. All rights reserved.*
