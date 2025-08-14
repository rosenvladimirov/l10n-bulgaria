# L10n BG Banking - Infopay Integration

This module provides integration with the Infopay API for importing bank statements and transactions from Bulgarian banks with **enhanced balance management**.

## Features

- **Session Management**: Automatic session creation and management for secure API communication
- **Simple Authentication**: Uses Client ID and Access Token for API authentication
- **Multi-Account Support**: Import transactions from multiple bank accounts
- **Currency Support**: Supports multiple currencies (defaults to BGN)
- **Transaction Import**: Import bank statements and transactions into Odoo
- **Connection Testing**: Built-in connection test functionality
- **🆕 Enhanced Balance Management**: Proper balance tracking and verification
- **🆕 Statement Balance Verification**: Verify statement balances against transaction amounts
- **🆕 API Balance Comparison**: Compare statement balances with current API balances
- **🆕 Running Balance Calculation**: Track running balances for each transaction

## Balance Management Features

### Enhanced Statement Import with Balances

The refactored statement import logic now properly handles balance information from the Infopay API:

- **Opening Balances**: Each statement includes the correct opening balance from the API
- **Closing Balances**: Statements are created with accurate closing balances
- **Transaction Balances**: Each transaction includes balance before and after
- **Running Balances**: Calculated running balances for verification purposes

### Balance Verification Tools

The module provides several tools to ensure statement accuracy:

1. **Statement Balance Verification**: Verify that statement balances are consistent with transaction amounts
2. **API Balance Comparison**: Compare statement closing balances with current API balances
3. **Balance Discrepancy Detection**: Automatic detection and reporting of balance mismatches
4. **Transaction Balance Tracking**: Track balance changes for each individual transaction

### Balance Data Structure

Each bank transaction now includes:

- `balance_before_transaction`: Account balance before this transaction
- `balance_after_transaction`: Account balance after this transaction  
- `running_balance`: Calculated running balance for verification
- `statement_id`: Link to the bank statement
- `statement_line_id`: Link to the statement line

## Technical Improvements

### Refactored Statement Import Logic

The statement import process has been completely refactored to handle balance data properly:

1. **API Balance Extraction**: The system now properly extracts balance information from the Infopay API response
2. **Transaction Sorting**: Transactions are sorted by date and time to ensure proper balance calculation
3. **Balance Calculation**: Running balances are calculated for each transaction
4. **Statement Creation**: Bank statements are created with proper opening and closing balances
5. **Balance Verification**: Automatic verification of balance consistency

### Enhanced Data Models

The `bank.transaction` model has been enhanced with:

- **Balance Fields**: New fields to store balance information from the API
- **Statement Links**: Direct links to bank statements and statement lines
- **Data Integrity**: Better data validation and consistency checks

### Improved Error Handling

The refactored code includes:

- **Balance Validation**: Automatic detection of balance discrepancies
- **Detailed Logging**: Comprehensive logging of balance calculations
- **User Notifications**: Clear feedback about balance verification results
- **Graceful Degradation**: System continues to work even with minor balance issues

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
   - **Integration Start Date**: Start date for transaction import from Infopay
   - **Integration End Date**: End date for transaction import from Infopay

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
3. Configure the **Integration Start Date** and **Integration End Date** fields
4. Click the **"Import Infopay Statement"** button
5. The system will:
   - Create a session with Infopay API
   - Use the configured Client ID and Access Token
   - Fetch available accounts
   - Import transactions for the specified date range
   - Create bank statement lines
   - Clean up the session

### Balance Verification and Management

#### Verifying Statement Balances

1. Navigate to **Accounting > Configuration > Bank Management > Bank Journals**
2. Select the bank journal you want to verify
3. Click the **"Verify Statement Balances"** button
4. The system will:
   - Check all statements for balance consistency
   - Compare opening + transaction amounts with closing balances
   - Report any discrepancies found
   - Show detailed balance information for each statement

#### Getting Current Balance from API

1. Navigate to **Accounting > Configuration > Bank Management > Bank Journals**
2. Select the bank journal you want to check
3. Click the **"Get Current Balance from API"** button
4. The system will:
   - Connect to Infopay API
   - Fetch current account balance
   - Compare with latest statement closing balance
   - Report any differences found

#### Viewing Transaction Balances

1. Navigate to **Accounting > Configuration > Bank Management > Bank Transactions**
2. View all imported transactions with balance information
3. Each transaction shows:
   - Balance before and after the transaction
   - Running balance for verification
   - Link to corresponding statement and line

### API Endpoints Used

The module uses the following Infopay API endpoints:

- **Session Management**: `POST /api/session` - Create a new session
- **Session Cleanup**: `POST /api/session/close` - Clean up session
- **Accounts**: `GET /api/accounts` - List available accounts
- **Transactions**: `GET /api/accounts/{account_id}/transactions` - Get transactions for an account with date range and balance

### Authentication Headers

The module sends the following headers with each API request:
- `SessionId: {session_id}` (for API calls)
- `SessionKey: {session_key}` (for API calls)
- `Accept: application/json`
- `Content-Type: application/json`

### Session Management

The module automatically handles session lifecycle:

1. **Session Creation**: Creates a new session before API operations
2. **Session Validation**: Checks if current session is still valid (24-hour expiry)
3. **Session Refresh**: Automatically creates new session if current one expires
4. **Session Cleanup**: Cleans up session after operations complete

### Transaction Import Parameters

When importing transactions, the module automatically includes:
- **Date Range**: Uses the configured Integration Start Date and End Date
- **Balance Information**: Always sets `withBalance=true` parameter
- **Account Filtering**: Automatically matches accounts by IBAN

### Error Handling

The module includes comprehensive error handling for:
- Missing credentials
- Session creation failures
- API communication errors
- Session expiration
- Invalid responses
- Missing date range configuration

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
6. **🆕 Balance Discrepancies**: Use the balance verification tools to identify and resolve issues
7. **🆕 Incorrect Statement Balances**: Verify that the API is returning correct balance information

### Balance-Specific Troubleshooting

#### Statement Balance Mismatches

If you encounter balance discrepancies:

1. **Use Balance Verification**: Run the "Verify Statement Balances" action to identify issues
2. **Check API Balances**: Use "Get Current Balance from API" to compare with current balances
3. **Review Transaction Order**: Ensure transactions are properly sorted by date and time
4. **Check Currency**: Verify that all amounts are in the same currency
5. **API Data Quality**: Some APIs may have timing issues with balance updates

#### Transaction Balance Issues

If individual transaction balances seem incorrect:

1. **Check Raw Data**: Review the raw data from the API for balance information
2. **Verify API Response**: Ensure the API is returning balance data with each transaction
3. **Check Date Ranges**: Balance calculations depend on proper transaction ordering
4. **Review Logs**: Check Odoo logs for balance calculation warnings

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
