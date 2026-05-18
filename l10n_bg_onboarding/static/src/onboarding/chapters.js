/** @odoo-module **/
/*
 * Разказвателен слой върху backend вертикалите. Само презентация —
 * истината (state/progress/steps) идва от l10n.bg.vertical. UI копи на
 * английски (правило). Ключ = vertical.code (V0…V12); има generic
 * fallback за непознат код.
 */

export const CHAPTERS = {
    V0: { kicker: "Foundation", line: "Lay the ground — country, chart of accounts, your company identity.", seed: 0, lottie: "v0.json" },
    V1: { kicker: "People & Places", line: "Partners and geography, bilingual and transliterated.", seed: 1, lottie: "v1.json" },
    V2: { kicker: "Accounting Core", line: "Tailor the chart to your KID activity sectors.", seed: 2, lottie: "v2.json" },
    V3: { kicker: "VAT & NRA", line: "Ledgers and declarations, ready for the Revenue Agency.", seed: 3, lottie: "v3.json" },
    V4: { kicker: "Banking", line: "Borica InfoPay — statements and payments flowing in.", seed: 0, lottie: "v4.json" },
    V5: { kicker: "Fiscal Devices", line: "Fiscal printers, wired through the IoT bridge.", seed: 1, lottie: "v5.json" },
    V6: { kicker: "Payroll", line: "Bulgarian payroll and the NRA payroll declarations.", seed: 2, lottie: "v6.json" },
    V7: { kicker: "Manufacturing", line: "Material consumption through the 601 transit, cleared to 611.", seed: 3, lottie: "v7.json" },
    V8: { kicker: "Documents", line: "Professional Bulgarian document layouts.", seed: 0, lottie: "v8.json" },
    V9: { kicker: "Intrastat", line: "Intra-Community trade — declared and exported.", seed: 1, lottie: "v9.json" },
    V10: { kicker: "Tax Assistant", line: "VAT protocols, customs, fiscal-position routing.", seed: 2, lottie: "v10.json" },
    V11: { kicker: "AI & Tooling", line: "In-Odoo assistant and document intelligence.", seed: 3, lottie: "v11.json" },
    V12: { kicker: "Access Control", line: "Two-channel access — credential and camera.", seed: 0, lottie: "v12.json" },
};

export function chapterFor(code) {
    return (
        CHAPTERS[code] || {
            kicker: "Localization",
            line: "Configure this section to continue.",
            seed: 0,
            lottie: null,
        }
    );
}
