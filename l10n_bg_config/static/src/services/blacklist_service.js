/** @odoo-module **/

/**
 * BLC Blacklist Service
 *
 * Проверява на всеки час дали текущата фирма е в блекълиста на нелоялни клиенти.
 * При мач: показва sticky жълто съобщение чрез notification service.
 * При липсващ/повреден файл: показва non-dismissable overlay (блокира приложението).
 *
 * Комуникира и чрез bus канал "l10n_bg_blacklist" за real-time нотификации.
 */

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";

const CHECK_INTERVAL_MS = 60 * 60 * 1000; // 1 час

const blacklistService = {
    dependencies: ["notification", "bus_service"],

    start(env, { notification, bus_service }) {
        let warningActive = false;

        // ── Overlay (блокиращ екран) ──────────────────────────────────────────
        const showBlockedOverlay = () => {
            if (document.getElementById("l10n-bg-blacklist-overlay")) return;

            const overlay = document.createElement("div");
            overlay.id = "l10n-bg-blacklist-overlay";
            overlay.innerHTML = `
                <div class="l10n-bg-blocked-box">
                    <div class="l10n-bg-blocked-icon">⛔</div>
                    <h2>Module Configuration Error</h2>
                    <p>
                        The BLC localization security file is missing or corrupted.<br/>
                        The application cannot continue until this is resolved.
                    </p>
                    <p class="l10n-bg-blocked-contact">
                        Contact your system administrator or <strong>support@bl-consulting.net</strong>
                    </p>
                </div>`;
            document.body.appendChild(overlay);
        };

        // ── Sticky жълто предупреждение ───────────────────────────────────────
        const showWarning = (message) => {
            if (warningActive) return;
            warningActive = true;

            notification.add(message, {
                type: "warning",
                sticky: true,
                className: "l10n_bg_blacklist_warning",
                onClose: () => {
                    warningActive = false;
                },
            });
        };

        // ── Основна проверка ──────────────────────────────────────────────────
        const checkBlacklist = async () => {
            let result;
            try {
                result = await rpc("/l10n_bg/blacklist/check");
            } catch (err) {
                // Мрежова грешка — не блокираме, само логваме.
                console.warn("[l10n_bg] Blacklist check failed:", err);
                return;
            }

            if (result.status === "blocked") {
                showBlockedOverlay();
                return;
            }

            if (result.blacklisted) {
                const msg =
                    `⚠ ${result.message || "This company is not authorized to use BLC modules."}`;
                showWarning(msg);
            }
        };

        // ── Старт: проверка след 5 сек (да не забавя зареждането) ────────────
        browser.setTimeout(checkBlacklist, 5_000);

        // ── Периодична проверка на всеки 1 час ───────────────────────────────
        browser.setInterval(checkBlacklist, CHECK_INTERVAL_MS);

        // ── Bus: real-time push от сървъра (при промяна на файла) ─────────────
        bus_service.subscribe("l10n_bg_blacklist", (payload) => {
            if (!payload) return;
            if (payload.type === "blocked") {
                showBlockedOverlay();
            } else if (payload.type === "warning" && payload.message) {
                showWarning(payload.message);
            }
        });
    },
};

registry.category("services").add("l10n_bg_blacklist", blacklistService);
