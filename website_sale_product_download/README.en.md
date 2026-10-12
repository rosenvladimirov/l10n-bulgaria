# eCommerce: Free Product Download

Free downloads in the shop, the way the Odoo Apps store works: a **Download**
button on the product page instead of **Add to Cart**.

## Configuration

1. Create a product with a zero sales price and, if it comes in several
   builds, an attribute for them (for example *Operating System*: Windows,
   Linux) that creates variants.
2. On each variant add a document (Documents smart button) with
   *Sale: Visible at* = **On confirmed order**. A document on the product
   template is used for variants without their own.
3. Tick **Free Download** in the *Ecommerce Shop* group of the product form
   and publish the product.

## Usage

The visitor picks the variant and clicks **Download**. Visitors who are not
signed in go through the login or sign-up page and come back to the same
variant. The download starts at once; no order is created.

Every download is logged (*Website → eCommerce → Orders → Downloads*, and the
*Downloads* smart button on the product) with the customer, the variant and
the file.

## Rules

- Only products with a zero sales price can be marked; a variant whose price
  on the website pricelist is not zero is not given away.
- Only published products of the current website, and only documents visible
  on confirmed orders.
