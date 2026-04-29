To use this module:

## Fiscal Receipt Printing (Automatic)

When completing a sale in POS:

1. Add products to cart as usual
2. Click **Payment**
3. Select payment method (cash/card)
4. Click **Validate**

The system automatically prints the fiscal receipt. No manual intervention needed!

## X Report (Intermediate Report)

To print an X report during the session:

- Go to **Point of Sale → Dashboard → Sessions**
- Open your active session
- Click **X Report** button in the header

The report is printed on the fiscal printer without resetting daily counters.

## Z Report (Daily Report with Reset)

To close the day and print Z report:

- Go to **Point of Sale → Dashboard → Sessions**
- Open your session
- Click **Z Report** button in the header
- Confirm the dialog
- Session can now be closed

⚠️ **Warning**: Z Report resets daily counters. Run only once per day!

## Cash Operations

**Deposit (Служебно въведени):**

- Open your active session
- Click **Служебно въведени** button
- Enter amount and reason
- Click **Execute**

**Withdraw (Служебно изведени):**

- Open your active session
- Click **Служебно изведени** button
- Enter amount and reason
- Click **Execute**

## Viewing Fiscal Data

To see fiscal receipt information:

- Go to **Point of Sale → Orders → Orders**
- Open any paid order
- See **Fiscal Number**, **Fiscal DateTime**, and **Fiscal Memory** fields

You can also filter orders by:
- **With Fiscal Receipt**
- **Without Fiscal Receipt**

## Monitoring Printer Status

To check printer status:

- Go to **Point of Sale → Configuration → Fiscal Printers → Devices**
- Open a device
- See **Current Status** and **Status History**
- Click **Update Status** to refresh
