Translate every element of an eCommerce product page from the backend, in one
wizard, the same way the translation dialog works for a view (`arch_db`):
term by term, with the source next to the translation for each language.

The wizard is opened from the **Translate Page** button on the product form and
collects:

- **Product**: name, sales description, eCommerce description, the full
  description below the product (`website_description`), SEO fields (meta
  title, description, keywords, SEO name), the ribbon and the base unit.
- **Attributes**: the attributes and the values used by the product.
- **Categories and Tags**: the public categories of the product and their
  parents (shown in the breadcrumb), and the product tags.
- **Page Layout**: every template the product page is rendered from. The
  wizard starts at `website_sale.product` and follows the static `t-call`s
  (price, add-to-cart button, variants, accordion, terms and conditions...),
  together with the active extensions of each template for the selected
  website: the page options and the blocks dropped with the website editor.
  For each template the copy of the selected website is used when one exists
  (copy-on-write), i.e. the view the website actually renders. The site-wide
  layout (header, footer, menu) is not part of the product page and is left
  out. Texts without a single letter (punctuation, sizes such as "180×100×50")
  are skipped.

HTML fields and views are split into terms; plain fields are translated as a
whole. Saving goes through the standard `update_field_translations`, so no
translation is stored outside the records themselves and access rights are
the regular ones: page layout terms are shown only to users who may write
views.

The source column is always the `en_US` value, as in the standard
translation dialog. The `en_US` line, when selected, edits the source itself.

Texts rendered by JavaScript (for example the product configurator dialog
and the cart notifications) are code translations from the modules' `.po`
files and are not stored on records, so they cannot be edited here.

Other modules can add elements to the wizard by extending
`_get_translation_targets()`.
