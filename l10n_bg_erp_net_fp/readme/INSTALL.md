To install this module, you need to:

1. Install ErpNet.FP server (external dependency)

   Using Docker:

   ```bash
   docker run -d --name erpnetfp -p 8001:8001 -v /dev/usb:/dev/usb --privileged rosenvladimirov/erpnetfp:latest
   ```

   Or download standalone from: https://github.com/erpnet/ErpNet.FP

2. Install Python dependencies (already included in Odoo):

   ```bash
   pip install requests
   ```

3. Clone the module repository:

   ```bash
   cd /path/to/odoo/addons
   git clone https://github.com/rosenvladimirov/l10n-bulgaria.git
   ```

4. Restart Odoo:

   ```bash
   sudo systemctl restart odoo
   ```

5. Update Apps List in Odoo:

  - Go to Apps menu
  - Click "Update Apps List"

6. Install the module:

  - Search for "ErpNet.FP"
  - Click Install

Note: Make sure ErpNet.FP server is accessible from Odoo server on port 8001 (or configured port).[ This file must only be present if there are very specific
  installation instructions, such as installing non-python
  dependencies. The audience is systems administrators. ]

