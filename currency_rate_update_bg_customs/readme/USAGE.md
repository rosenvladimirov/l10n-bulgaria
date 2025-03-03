
The **currency_rate_update_bg_customs** module simplifies the process of keeping exchange rates up-to-date in Odoo, ensuring compliance with Bulgarian customs regulations. Follow these steps to effectively use the module:
## 1. Activate the Module
- Ensure the **currency_rate_update_bg_customs** module is installed in your Odoo instance. You can confirm this by navigating to **Apps** and checking the status of the module.

## 2. Enable Currency Rate Updates
1. Go to **Settings** → **General Settings**.
2. Scroll down to the **Currency Exchange Rate Update** section.
3. Select **Bulgarian Customs** as the provider for automatic exchange rate updates.
4. Enable the **Automatic Updates** feature for seamless integration.

## 3. Configure Currencies
1. Navigate to **Accounting** → **Configuration** → **Currencies**.
2. Ensure that all the currencies you use (e.g., BGN, EUR, USD) are active.
3. Verify that the base currency (e.g., BGN) is set correctly and that it displays exchange rates obtained from customs.

## 4. Schedule Automatic Updates
1. Go to **Settings** → **Technical** → **Automation** → **Scheduled Actions**.
2. Find the action named **Update Currency Rates** and click to configure.
3. Set the frequency (e.g., “Every Day”) to ensure regular updates of exchange rates.
4. Save the configuration.

## 5. Manually Update Exchange Rates (Optional)
1. If needed, you can perform a manual update at any time.
    - Go to **Accounting** → **Configuration** → **Currencies**.
    - Select a currency and click the **Update Rates** button.

2. This will fetch the latest rates from the Bulgarian Customs Authorities.

## 6. Verify The Exchange Rates
1. Go to **Accounting** → **Configuration** → **Currencies**.
2. Check the **Latest Rate** column to ensure the exchange rates were updated correctly.
3. Use the logs in **Settings** → **Technical** → **Logs** to troubleshoot any issues, if necessary.

## Additional Tips
- If you handle frequent import/export activities, ensure the scheduler is set for daily updates so your exchange rates reflect the latest customs data.
- Always verify that the imported rates are in line with the official rates published by Bulgarian Customs.

By following these steps, you can efficiently use the **currency_rate_update_bg_customs** module to streamline currency rate management for customs-related calculations and ensure compliance with Bulgarian legal regulations.
