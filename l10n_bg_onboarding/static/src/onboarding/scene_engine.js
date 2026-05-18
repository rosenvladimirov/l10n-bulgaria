/** @odoo-module **/
/*
 * Сцена-двигател: Lottie ако е наличен (vendored lib + JSON по ключ),
 * иначе елегантен анимиран SVG-мотив (шевица геометрия). Така onboarding-ът
 * е красив дори преди да се пуснат Lottie JSON активи — Lottie е drop-in
 * подобрение, не предусловие.
 */
import { loadJS } from "@web/core/assets";

const LOTTIE_LIB = "/l10n_bg_onboarding/static/lib/lottie/lottie-web.min.js";
let _lottieTried = false;
let _lottie = null;

export async function ensureLottie() {
    if (_lottieTried) {
        return _lottie;
    }
    _lottieTried = true;
    try {
        await loadJS(LOTTIE_LIB);
        _lottie = window.lottie || window.bodymovin || null;
    } catch (_e) {
        _lottie = null; // тихо → SVG fallback
    }
    return _lottie;
}

// шевица палитри по глава (ротация ink/rose/gold/forest)
const PALETTES = [
    ["#C2304B", "#E8C268"],
    ["#C8A24A", "#7A1F33"],
    ["#3F7A5E", "#E8C268"],
    ["#B5314C", "#2C6E63"],
];

/* Параметричен cross-stitch SVG-мотив: ромбовидна решетка от
 * „бодове", който се сглобява анимирано (stagger). Различен seed на
 * глава → разпознаваема, неповтаряща се илюстрация. */
function buildMotifSVG(seed) {
    const [a, b] = PALETTES[seed % PALETTES.length];
    const cells = [];
    const N = 7;
    for (let r = 0; r < N; r++) {
        for (let c = 0; c < N; c++) {
            const onDiag =
                (r + c) % 2 === ((seed % 2) === 0 ? 0 : 1);
            const inDiamond = Math.abs(r - 3) + Math.abs(c - 3) <= 3;
            if (!inDiamond) {
                continue;
            }
            const x = c * 28 + 14;
            const y = r * 28 + 14;
            const fill = onDiag ? a : b;
            const delay = ((Math.abs(r - 3) + Math.abs(c - 3)) * 70) + "ms";
            cells.push(
                `<g class="bgob-stitch" style="animation-delay:${delay}">` +
                    `<path d="M${x - 9} ${y} L${x} ${y - 9} L${x + 9} ${y} ` +
                    `L${x} ${y + 9} Z" fill="${fill}"/>` +
                    `<path d="M${x - 4} ${y} L${x} ${y - 4} L${x + 4} ${y} ` +
                    `L${x} ${y + 4} Z" fill="#0E0B0C" opacity=".35"/>` +
                    `</g>`
            );
        }
    }
    return (
        `<svg class="bgob-motif" viewBox="0 0 224 224" ` +
        `xmlns="http://www.w3.org/2000/svg" aria-hidden="true">` +
        `<g class="bgob-motif-rot">${cells.join("")}</g></svg>`
    );
}

/**
 * Монтира сцена в `el`. `chapter.lottie` = относителен JSON път
 * (по избор; ако липсва или Lottie не е наличен → SVG-мотив).
 * Връща обект с .destroy().
 */
export async function mountScene(el, chapter) {
    if (!el) {
        return { destroy() {} };
    }
    el.innerHTML = "";
    const lib = chapter.lottie ? await ensureLottie() : null;
    if (lib && chapter.lottie) {
        try {
            const anim = lib.loadAnimation({
                container: el,
                renderer: "svg",
                loop: true,
                autoplay: true,
                path:
                    "/l10n_bg_onboarding/static/src/anim/" +
                    chapter.lottie,
            });
            return {
                destroy() {
                    try {
                        anim.destroy();
                    } catch (_e) {
                        /* noop */
                    }
                },
            };
        } catch (_e) {
            /* падаме към SVG */
        }
    }
    el.innerHTML = buildMotifSVG(chapter.seed || 0);
    return { destroy() { el.innerHTML = ""; } };
}
