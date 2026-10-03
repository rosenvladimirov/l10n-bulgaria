Restores the field translation button on translatable fields rendered with the
`field_partner_autocomplete` widget (the company name on a partner of type
*Company* and the company name on `res.company`).

In the core `partner_autocomplete` module the template
`partner_autocomplete.PartnerAutoCompleteCharField` inserts a `t-elif` branch
with the `<PartnerAutoComplete>` component before the `t-else` branch of
`web.CharField`. The `TranslationButton` lives only in that `t-else` branch, so
whenever the autocomplete branch is active the button is not rendered, even
when the field is translatable (for example with `partner_multilang`).

This module only extends that template: it adds the same
`o_field_input_buttons` wrapper with a `TranslationButton` right after the
autocomplete input when the field is translatable, plus the minimal styling to
position it like on a regular char field. No Python or JavaScript logic is
changed; `TranslationButton` and `isTranslatable` are already provided by the
component inherited from `CharField`.
