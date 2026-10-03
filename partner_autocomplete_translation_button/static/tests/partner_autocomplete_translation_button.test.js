// Проверява, че field_partner_autocomplete показва бутона за превод в клона
// с автодовършване (фирма), когато полето е преводимо, и не го показва за
// непреводимо поле. Образец: partner_autocomplete/static/tests и
// web/static/tests/views/fields/char_field.test.js („char field translatable“).
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    mountView,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

class ResPartner extends mailModels.ResPartner {
    // Името е преводимо — така е при partner_multilang в тази локализация.
    name = fields.Char({ translate: true });
    company_type = fields.Selection({
        string: "Company Type",
        selection: [
            ["company", "Company"],
            ["individual", "Individual"],
        ],
    });
    _records = [
        ...mailModels.ResPartner._records,
        { id: 1001, name: "Терарос", company_type: "company", vat: "BG123456789" },
    ];
    _views = {
        form: `
            <form>
                <field name="company_type"/>
                <field name="name" widget="field_partner_autocomplete"/>
                <field name="vat" widget="field_partner_autocomplete"/>
            </form>
        `,
    };
}

defineModels({ ...mailModels, ResPartner });

const FIELD = ".o_field_field_partner_autocomplete";

test("translatable field keeps the translation button in the autocomplete branch", async () => {
    serverState.lang = "en_US";
    serverState.multiLang = true;
    await mountView({ type: "form", resModel: "res.partner", resId: 1001 });

    // Клонът с автодовършване наистина е активен (фирма), не t-else на CharField.
    expect(`${FIELD}[name=name] .o-autocomplete input.o-autocomplete--input`).toHaveCount(1);
    // Бутонът за превод е до автодовършването, в обвивката на ядрото.
    expect(
        `${FIELD}[name=name] > .o-autocomplete + .o_field_input_buttons .btn.o_field_translate`
    ).toHaveCount(1);
    // toHaveText чете innerText, а скритият (visibility: hidden) бутон дава "" —
    // фокусираме входа, за да стане видим, както в char_field.test.js на ядрото.
    await contains(`${FIELD}[name=name] .o-autocomplete--input`).click();
    expect(`${FIELD}[name=name] .btn.o_field_translate`).toHaveText("EN");
});

test("non-translatable field gets no translation button", async () => {
    serverState.lang = "en_US";
    serverState.multiLang = true;
    await mountView({ type: "form", resModel: "res.partner", resId: 1001 });

    expect(`${FIELD}[name=vat] .o-autocomplete`).toHaveCount(1);
    expect(`${FIELD}[name=vat] .o_field_input_buttons`).toHaveCount(0);
    expect(`${FIELD}[name=vat] .btn.o_field_translate`).toHaveCount(0);
});

test("translation button opens the translation dialog", async () => {
    serverState.lang = "en_US";
    serverState.multiLang = true;
    onRpc("res.lang", "get_installed", () => [
        ["en_US", "English"],
        ["bg_BG", "Bulgarian"],
    ]);
    onRpc("res.partner", "get_field_translations", () => [
        [
            { lang: "en_US", source: "Терарос", value: "Teraros" },
            { lang: "bg_BG", source: "Терарос", value: "Терарос" },
        ],
        { translation_type: "char", translation_show_source: false },
    ]);
    await mountView({ type: "form", resModel: "res.partner", resId: 1001 });

    // Бутонът е с visibility: hidden, докато полето няма :hover/:focus-within,
    // а contains() чака видим елемент — затова първо фокусираме входа (както
    // в char_field.test.js на ядрото). Кликът по входа отваря автодовършването
    // без търсене (заявка "" не минава validateSearchTerm), така че няма RPC.
    await contains(`${FIELD}[name=name] .o-autocomplete--input`).click();
    await contains(`${FIELD}[name=name] .btn.o_field_translate`).click();
    expect(".modal .o_translation_dialog .translation").toHaveCount(2);
});
