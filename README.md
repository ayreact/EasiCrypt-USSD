## EasiCrypt USSD

# Overview:
A Flask-based backend structured as a modular system for a **USSD-enabled dApp** management platform. It allows developers to register and authenticate, create and manage apps, and define endpoint URLs for wallet-related operations (like verifying users, sending crypto, fetching balances, and off-ramping). It integrates MongoDB for persistent storage and Redis for both caching sessions (USSD sessions) and rate limiting. JWT handles authentication, and cryptographic utilities (AES + bcrypt) ensure secure handling of sensitive data and PINs.

# Core Functional Flow:

**Authentication:** Developers can sign up, log in, refresh tokens, and reset passwords via secure JWT-based routes.

**App Management:** Authenticated developers can create, list, update, and delete apps, with ownership enforced via decorators.

**USSD Logic Support:** Redis-based session management exists for tracking per-session states.

**Security Layer:** All sensitive fields (PINs, codes) are hashed or encrypted using AES-256.

**Event Tracking:** The system can log app and user events to MongoDB for analytics or auditing.

**Rate Limiting:** Flask-Limiter is designed to prevent abuse per phone/session.