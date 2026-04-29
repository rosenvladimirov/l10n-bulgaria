To configure this module, you need to:

## 1. Install ErpNet.FP Server

First, install the ErpNet.FP server (recommended via Docker):
bash docker run -d --name erpnetfp -p 8001:8001 -v /dev/usb:/dev/usb --privileged rosenvladimirov/erpnetfp:latest
Or download from: https://github.com/erpnet/ErpNet.FP

## 2. Configure Fiscal Printer Device

- Go to **Point of Sale → Configuration → Fiscal Printers → Devices**
- Click **Create**
- Fill in:
  - **Name**: "My Fiscal Printer" (example)
  - **Host**: `http://localhost:8001` (or your ErpNet.FP server URL)
  - **Printer ID**: Get this from ErpNet.FP (e.g., "FP_12345")
  - **SSL Verify**: Disable if using self-signed certificates
  - **Timeout**: 30 seconds (default)
  - **Retry Count**: 3 (default)
- **Save**

## 3. Configure Automatic Z Reports (Optional)

In the same Fiscal Printer Device form:

- Enable **Automatic Z Report**
- Set **Z Report Hour**: 23 (11 PM)
- Set **Z Report Minute**: 59
- **Save**

## 4. Configure POS Terminal

- Go to **Point of Sale → Configuration → Point of Sale**
- Select your POS
- Open **Fiscal Printer** page/tab
- Select the **Fiscal Printer** device from step 2
- Enable **Automatic Z Report on Close** (recommended)
- **Save**

## 5. Configure Tax Groups

- Go to **Accounting → Configuration → Tax Groups**
- For each tax group used in POS, set **Tax Group for Fiscal Printer**:
  - **А** = VAT 0%
  - **Б** = VAT 20%
  - **В** = VAT 20% (alternative)
  - **Г** = VAT 9%
- **Save**

Configuration is complete! The module will now automatically print fiscal receipts when completing sales in POS.
