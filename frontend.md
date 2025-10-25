# EasiCrypt USSD Backend Integration Documentation

This documentation provides comprehensive guidance for frontend developers to integrate with the EasiCrypt USSD backend. It covers all API endpoints, authentication requirements, and integration details.

## Base URL
All API endpoints are prefixed with `/api`. The base URL depends on your deployment environment:
- Development: `http://localhost:5000/api`
- Production: `https://your-domain.com/api`

## Authentication
All endpoints except `/auth/signup` and `/auth/login` require JWT authentication. Include the JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## API Endpoints

### Authentication Endpoints

#### 1. Developer Signup
**Endpoint:** `POST /auth/signup`

**Request Body:**
```json
{
  "username": "developer_username",
  "email": "developer@example.com",
  "password": "secure_password"
}
```

**Response (Success - 201 Created):**
```json
{
  "message": "Developer created successfully",
  "developer_id": "507f1f77bcf86cd799439011"
}
```

**Response (Error - 400 Bad Request):**
```json
{
  "message": "Missing required fields"
}
```

#### 2. Developer Login
**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "email": "developer@example.com",
  "password": "secure_password"
}
```

**Response (Success - 200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (Error - 400 Bad Request):**
```json
{
  "message": "Missing email or password"
}
```

#### 3. Developer Logout
**Endpoint:** `POST /auth/logout`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (Success - 200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

#### 4. Token Refresh
**Endpoint:** `POST /auth/refresh`

**Headers:**
```
Authorization: Bearer <refresh_token>
```

**Response (Success - 200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### 5. Password Reset
**Endpoint:** `POST /auth/reset-password`

**Request Body:**
```json
{
  "email": "developer@example.com",
  "new_password": "new_secure_password"
}
```

**Response (Success - 200 OK):**
```json
{
  "message": "Password reset successfully"
}
```

### Apps Management Endpoints

#### 1. Create App
**Endpoint:** `POST /apps/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "app_name": "My DeFi App"
}
```

**Response (Success - 201 Created):**
```json
{
  "message": "App created successfully",
  "app_id": "507f1f77bcf86cd799439012"
}
```

#### 2. List Developer Apps
**Endpoint:** `GET /apps/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (Success - 200 OK):**
```json
[
  {
    "_id": "507f1f77bcf86cd799439012",
    "developer_id": "507f1f77bcf86cd799439011",
    "app_name": "My DeFi App",
    "visible": false,
    "endpoints": {
      "verify_endpoint": null,
      "send_endpoint": null,
      "get_balance_endpoint": null,
      "off_ramp_endpoint": null
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### 3. Update App
**Endpoint:** `PUT /apps/<app_id>`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body (partial update supported):**
```json
{
  "app_name": "Updated App Name",
  "visible": true,
  "endpoints": {
    "verify_endpoint": "https://myapp.com/api/verify",
    "send_endpoint": "https://myapp.com/api/send",
    "get_balance_endpoint": "https://myapp.com/api/balance",
    "off_ramp_endpoint": "https://myapp.com/api/offramp"
  }
}
```

**Response (Success - 200 OK):**
```json
{
  "message": "App updated successfully"
}
```

#### 4. Delete App
**Endpoint:** `DELETE /apps/<app_id>`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (Success - 200 OK):**
```json
{
  "message": "App deleted successfully"
}
```

### Analytics Endpoints

#### 1. Get App Metrics
**Endpoint:** `GET /analytics/<app_id>`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (Success - 200 OK):**
```json
{
  "app_id": "507f1f77bcf86cd799439012",
  "registrations": 50,
  "transactions": {
    "successful": 100,
    "failed": 5,
    "off_ramps": 10
  },
  "balance_checks": 75,
  "usage": {
    "daily_active_users_24h": 25
  },
  "system_endpoint_metrics_24h": {
    "verify_endpoint": {
      "total_calls": 60,
      "successful_calls": 55,
      "failure_rate": 8.33,
      "avg_latency_ms": 1200
    },
    "send_crypto": {
      "total_calls": 110,
      "successful_calls": 100,
      "failure_rate": 9.09,
      "avg_latency_ms": 1500
    }
  },
  "total_user_setups": 50
}
```

### USSD Integration

The USSD system handles user interactions through a session-based flow. All USSD requests are sent to:

**Endpoint:** `POST /ussd`

**Request Format (from USSD provider):**
```
sessionId=123456&serviceCode=*123#&phoneNumber=+2348012345678&text=1
```

**Response Format (to USSD provider):**
```
CON Welcome message
```
or
```
END Final message
```

#### USSD Flow Overview

1. **Initial Request:** User dials USSD code
2. **Main Menu:** Shows available apps including EasiCrypt Wallet
3. **App Selection:** User selects an app
4. **App-specific Flow:** Varies based on app type

#### EasiCrypt Wallet Flow
- Directly forwards to EasiCrypt Wallet API
- No setup required
- Handles all wallet operations externally

#### DeFi App Flow
1. **First-time Setup:**
   - Verification code input
   - PIN setup (4-digit)
2. **App Interaction:**
   - Send crypto
   - Check balance
   - Off-ramp
   - Change PIN

### External App Endpoints Requirements

For DeFi apps to integrate with EasiCrypt USSD, they must provide the following endpoints:

#### 1. Verification Endpoint
**Purpose:** Verify user's identity during setup
**Method:** `POST`
**URL:** Your provided `verify_endpoint`

**Request Body:**
```json
{
  "code": "user_verification_code",
  "phone_number": "+2348012345678"
}
```

**Expected Response (Success):**
```json
{
  "status": "success",
  "message": "Verification successful"
}
```

**Expected Response (Failure):**
```json
{
  "status": "failed",
  "message": "Invalid verification code"
}
```

#### 2. Send Crypto Endpoint
**Purpose:** Process cryptocurrency transfers
**Method:** `POST`
**URL:** Your provided `send_endpoint`

**Request Body:**
```json
{
    "amount": 10.5,
    "token_symbol": "USDC", // One of ETH, DAI, USDC, LINK
    "code": "SENDER_USER_CODE", 
    "recipient_code": "RECIPIENT_USER_CODE" // OR "recipient_address": "0xABC123..."
}
```
Note: recipient_code will be present if the recipient is registered with the same DeFi app. recipient_address will be present if the recipient is an external wallet. Your endpoint should handle both cases.

**Expected Response (Success):**
```json
{
  "status": "success",
  "message": "Transaction completed successfully",
  "transaction_hash": "0x1234..."
}
```

**Expected Response (Failure):**
```json
{
  "status": "failed",
  "message": "Insufficient balance"
}
```

#### 3. Get Balance Endpoint
**Purpose:** Retrieve user's balance
**Method:** `GET`
**URL:** Your provided `get_balance_endpoint`

**Query Parameters:**
```json
{
    "code": "USER_VERIFICATION_CODE"
}
```

**Expected Response (Success):**
```json
{
    "status": "success",
    "message": "Balances retrieved",
    "balances": {
        "ETH": 0.1234,
        "DAI": 500.00,
        "USDC": 120.50,
        "LINK": 5.78
    }
}
```

#### 4. Off-Ramp Endpoint
**Purpose:** Convert crypto to fiat currency
**Method:** `POST`
**URL:** Your provided `off_ramp_endpoint`

**Request Body:**
```json
{
    "code": "USER_VERIFICATION_CODE",
    "amount": 5000.00,
    "token_symbol": "USDC", // Will always be USDC
    "bank_name": "First Bank", 
    "account_number": "1234567890" 
}
```

**Expected Response (Success):**
```json
{
  "status": "success",
  "message": "Off-ramp request submitted",
  "reference": "OFF123456"
}
```

### Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Successful operation
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Invalid or missing authentication
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

Error responses include a message field:
```json
{
  "message": "Error description"
}
```

### Rate Limiting

- Authentication endpoints: 100 requests per minute
- USSD endpoint: 100 requests per minute
- Other endpoints: Configurable based on deployment

### Security Considerations

1. **JWT Tokens:** Store securely and refresh when expired
2. **HTTPS:** Always use HTTPS in production
3. **Input Validation:** Validate all user inputs
4. **Error Messages:** Avoid exposing sensitive information in error responses

### Testing

Use the following test credentials for development:

```json
{
  "email": "test@example.com",
  "password": "testpassword123"
}
```

### Support

For integration issues or questions, contact:
- Email: support@easicrypt.com
- Documentation: https://docs.easicrypt.com
- API Status: https://status.easicrypt.com