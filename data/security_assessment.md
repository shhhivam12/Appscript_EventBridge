# Security Assessment & Enhancement Plan

This document details the security architecture of the Apps Script EventBridge application, evaluates how API keys are generated, examines storage encryption risks, and outlines recommended security enhancements.

---

## 1. Current Security Mechanisms

### Authentication & Authorization
* **OAuth 2.0 Integration**: Third-party Google sign-in is authenticated using standard Google OAuth 2.0 workflows. The application requests standard scopes to run Google Apps Script projects and access drive/sheets resources.
* **Flask Session Management**: User sessions are stored server-side and signed with a cryptographically secure `SECRET_KEY` (either loaded from `.env` or generated at runtime using `os.urandom(32)`).
* **API Key Validation**: Webhook triggers use request header, query, or body verification of unique client API keys to match incoming payloads to active workflows.

---

## 2. API Key Generation

API keys and secrets are generated during credential creation within `services/storage.py` using Python's `os.urandom()` function, which delegates to the operating system's cryptographically secure pseudorandom number generator (CSPRNG):

```python
# API Key generation logic
"api_key": f"asb_{os.urandom(16).hex()}"     # 32 characters of random hex
"api_secret": os.urandom(24).hex()          # 48 characters of random hex
```
* **Security Level**: Excellent entropy. Since the values are random, it is impossible for attackers to guess or brute-force valid keys.

---

## 3. Storage Encryption Review

> [!WARNING]
> **Risk Check: Cleartext Storage**
> Currently, all user configurations, API credentials, third-party webhook secret bot tokens, Gemini API keys, and Google OAuth refresh tokens are stored in **plaintext JSON files** inside the `data/` directory:
> * [credentials.json](file:///c:/Shivam/codes/appscript-bridge/data/credentials.json)
> * [google_tokens.json](file:///c:/Shivam/codes/appscript-bridge/data/google_tokens.json)
> * [settings.json](file:///c:/Shivam/codes/appscript-bridge/data/settings.json)
>
> If the host server is compromised, or if data backups are improperly secured, these credentials can be leaked.

---

## 4. Recommended Security Enhancements

To bring the Apps Script EventBridge platform to enterprise security standards, we recommend implementing the following security additions:

### A. Encryption at Rest (Symmetric Key Encryption)
Encrypt sensitive fields (like Google OAuth refresh tokens, Gemini keys, Telegram bot tokens, and ServiceNow OAuth secrets) using AES-256 before writing them to the JSON files.
* **Mechanism**: Use the `cryptography` library's `Fernet` (symmetric encryption).
* **Key Management**: Store a unique `ENCRYPTION_KEY` in the server's `.env` file (do NOT check this key into Git).
* **Usage**:
  ```python
  from cryptography.fernet import Fernet
  # Encryption key stored in env
  f = Fernet(os.getenv("ENCRYPTION_KEY"))
  encrypted_token = f.encrypt(token.encode())
  ```

### B. Hashing API Keys
Instead of storing API keys in plaintext inside `credentials.json`, store a cryptographic hash (e.g. SHA-256).
* When an external webhook requests `/webhook/trigger`, calculate the SHA-256 hash of the incoming header key and match it against the stored hashes.
* This prevents attackers from reading active API keys even if they obtain access to the database files.

### C. Webhook Rate Limiting
Apply rate-limiting on the `/webhook` endpoints using `Flask-Limiter` to protect the backend from Denial of Service (DoS) attacks and brute-force key validation attempts.
* Limit generic triggers to a maximum (e.g., 60 requests per minute per IP or per API key).

### D. Secure Webhook Validation
Validate signatures when possible for incoming payloads (e.g., verifying Telegram headers or ServiceNow mutual authentication tokens).
