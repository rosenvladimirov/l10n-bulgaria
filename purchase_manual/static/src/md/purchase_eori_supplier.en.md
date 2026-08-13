# 🆔 Supplier EORI Number

> Field: `res.partner.l10n_bg_eori` (added by `l10n_bg_tax_admin`) · Related model: `account.move.bg.customs`

## 📌 When to use
The EORI (Economic Operators Registration and Identification) number is a mandatory detail on **customs declarations** — i.e. for imports from non-EU countries or certain EU operations with customs handling. If the business only trades within Bulgaria/EU without customs procedures, this field is not required.

## ✅ Before you start
- The `l10n_bg_tax_admin` module must be installed (the `l10n_bg_eori` field only exists then — the standard `res.partner` has no such field).
- Know the vendor's EORI number (usually provided on their commercial documents, or verifiable through the European Commission's EORI validation system).

## 🧾 Step by step
1. Open the vendor's contact card (`res.partner`).
2. Find the **EORI Number** field (`l10n_bg_eori`) — usually in the tax/accounting details section.
3. Enter the EORI number exactly as registered (format: country code + identifier, e.g. `BG123456789`).
4. When generating a customs declaration from an import bill, the `partner_eori` field on `account.move.bg.customs` is auto-filled (related) from the vendor.

## 📂 What gets generated
- No new record is created — it fills an existing field on the vendor, which is then automatically carried into customs declarations.

## ⚠️ Common mistakes
- An empty EORI field on a non-EU vendor → the customs declaration will have incomplete data, which can complicate its processing.
- Confusing the EORI number with the company's regular VAT number — these are different identifiers.
- The field is not required for **all** vendors — only for those involved in customs procedures (import/export outside the EU, specific EU operations).

## 🔗 Related
For the full flow when importing from a third country — see *Importing from Outside the EU* in this manual and the *Outside EU — Purchase (Import)* scenario in the VAT administration manual.
