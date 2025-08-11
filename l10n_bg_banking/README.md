# L10n BG Banking - Infopay Integration

This module provides integration with the Infopay API for importing bank statements and transactions from Bulgarian banks.

## Features

- **Session Management**: Automatic session creation and management for secure API communication
- **Simple Authentication**: Uses Client ID and Access Token for API authentication
- **Multi-Account Support**: Import transactions from multiple bank accounts
- **Currency Support**: Supports multiple currencies (defaults to BGN)
- **Transaction Import**: Import bank statements and transactions into Odoo
- **Connection Testing**: Built-in connection test functionality

## Configuration

### 1. Infopay API Credentials

To use this module, you need to obtain API credentials from Infopay:

1. Register for an account at [Infopay Integration Platform](https://integration.infopay.bg)
2. Create a new application to get your Client ID
3. Obtain an Access Token for your application
4. Configure the necessary permissions for your application

### 2. Bank Configuration

1. Go to **Accounting > Configuration > Bank Management > Banks**
2. Select or create a bank record
3. Fill in the Infopay configuration fields:
   - **Infopay API URL**: Default is `https://integration.infopay.bg`
   - **Infopay Client ID**: Your Infopay application client ID
   - **Infopay Access Token**: Your Infopay access token
   - **Bank Code**: The bank code identifier
   - **Account IBAN**: The IBAN of the account to import

### 3. Journal Configuration

Ensure that your bank journals are properly configured with:
- Correct bank account IBAN
- Proper currency settings
- Bank account linked to the journal

## Usage

### Testing Connection

1. Navigate to **Accounting > Configuration > Bank Management > Banks**
2. Select the bank record you want to test
3. Click the **"Test Connection"** button
4. The system will:
   - Create a session with Infopay API
   - Test the accounts endpoint
   - Clean up the session
   - Show success/failure notification

### Importing Bank Statements

1. Navigate to **Accounting > Configuration > Bank Management > Banks**
2. Select the bank record you want to import statements for
3. Click the **"Import Infopay Statement"** button
4. The system will:
   - Create a session with Infopay API
   - Use the configured Client ID and Access Token
   - Fetch available accounts
   - Import transactions for matching IBANs
   - Create bank statement lines
   - Clean up the session

### API Endpoints Used

The module uses the following Infopay API endpoints:

- **Session Management**: `POST /api/session` - Create a new session
- **Session Cleanup**: `DELETE /api/session/{session_id}` - Clean up session
- **Accounts**: `GET /api/v1/accounts` - List available accounts
- **Transactions**: `GET /api/v1/accounts/{account_id}/transactions` - Get transactions for an account

### Authentication Headers

The module sends the following headers with each API request:
- `Authorization: Bearer {access_token}`
- `X-Client-ID: {client_id}`
- `X-Session-ID: {session_id}` (for API calls)
- `Accept: application/json`
- `Content-Type: application/json`

### Session Management

The module automatically handles session lifecycle:

1. **Session Creation**: Creates a new session before API operations
2. **Session Validation**: Checks if current session is still valid
3. **Session Refresh**: Automatically creates new session if current one expires
4. **Session Cleanup**: Cleans up session after operations complete

### Error Handling

The module includes comprehensive error handling for:
- Missing credentials
- Session creation failures
- API communication errors
- Session expiration
- Invalid responses

## Technical Details

### Session Management

The module implements a complete session management system:

1. **Session Creation**: `POST /api/session` with client_id, scope, and duration
2. **Session Validation**: Checks session expiry time
3. **Session Usage**: Includes session ID in all API requests
4. **Session Cleanup**: `DELETE /api/session/{session_id}` after operations

### Authentication Method

The module uses a session-based authentication:
1. **Client ID**: Identifies your application
2. **Access Token**: Provides API access authorization
3. **Session ID**: Provides session-specific context for API calls

### Data Mapping

The module maps Infopay API responses to Odoo models:

- **Account**: Maps to `res.bank` with Infopay-specific fields
- **Transactions**: Maps to `bank.transaction` model
- **Statements**: Creates bank statement lines from transactions

### Dependencies

- `base`: Core Odoo functionality
- `account`: Accounting module
- `account_bank_statement_import`: Bank statement import functionality

## Troubleshooting

### Common Issues

1. **Authentication Failed**: Check your Client ID and Access Token
2. **Session Creation Failed**: Verify your API permissions and credentials
3. **No Accounts Found**: Verify your API permissions and account access
4. **Session Expired**: The module should handle this automatically
5. **No Transactions**: Ensure the account IBAN matches between Infopay and Odoo

### Debug Information

Enable debug logging to see detailed API communication:
- Check Odoo logs for API request/response details
- Monitor session creation and cleanup
- Monitor transaction import progress

## Security Considerations

- Access tokens are stored as password fields (encrypted)
- Session IDs are managed automatically
- All API communication uses HTTPS
- Sessions are automatically cleaned up after operations
- Client ID and Access Token are required for all operations

## Support

For issues related to:
- **Infopay API**: Contact Infopay support
- **Module functionality**: Check the module documentation or contact the maintainers
