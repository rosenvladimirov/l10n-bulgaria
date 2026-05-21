/** @odoo-module **/
/*
 * Full-screen воден onboarding (OWL client action). Презентационен
 * слой върху l10n.bg.vertical engine — нула дублирана бизнес-логика;
 * всички действия минават през съществуващите step/wizard методи.
 */
import {
    Component,
    useState,
    useRef,
    onWillStart,
    onMounted,
    onPatched,
    onWillUnmount,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { mountScene } from "./scene_engine";
import { chapterFor } from "./chapters";

const V_FIELDS = ["code", "name", "state", "progress", "done", "sequence"];
const S_FIELDS = [
    "vertical_id",
    "name",
    "step_type",
    "module_name",
    "module_state",
    "state",
    "done",
    "optional",
    "registry_fetch",
    "sequence",
];

export class OnboardingApp extends Component {
    static template = "l10n_bg_onboarding.App";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.sceneRef = useRef("scene");
        this._scene = null;
        this._sceneKey = null;
        this.state = useState({
            phase: "hero", // hero | chapter | finale
            idx: 0,
            loading: true,
            busy: false,
            verticals: [],
            steps: {}, // vId -> [step,...]
            vatEik: "",
            error: "",
        });

        onWillStart(async () => {
            await this._load();
        });
        onMounted(() => this._syncScene());
        onPatched(() => this._syncScene());
        onWillUnmount(() => this._destroyScene());
    }

    // ── данни ───────────────────────────────────────────────────────
    async _load() {
        this.state.loading = true;
        const verticals = await this.orm.searchRead(
            "l10n.bg.vertical",
            [],
            V_FIELDS,
            { order: "sequence, code" }
        );
        const ids = verticals.map((v) => v.id);
        const steps = ids.length
            ? await this.orm.searchRead(
                  "l10n.bg.vertical.step",
                  [["vertical_id", "in", ids]],
                  S_FIELDS,
                  { order: "vertical_id, sequence, id" }
              )
            : [];
        const byV = {};
        for (const s of steps) {
            const vid = Array.isArray(s.vertical_id)
                ? s.vertical_id[0]
                : s.vertical_id;
            (byV[vid] = byV[vid] || []).push(s);
        }
        this.state.verticals = verticals;
        this.state.steps = byV;
        // Auto-seed vatEik от company.vat (db_installer го попълва от
        // ir.config_parameter.l10n_bg.pending_vat_eik при post-install).
        // Така Trade Register fetch на V0 става без user input.
        if (!this.state.vatEik) {
            try {
                const cmp = await this.orm.searchRead(
                    "res.company",
                    [],
                    ["vat"],
                    { limit: 1, order: "id" }
                );
                if (cmp.length && cmp[0].vat) {
                    this.state.vatEik = cmp[0].vat;
                }
            } catch (e) {
                // graceful — vat field може да липсва ако l10n_bg_config
                // не е installed още
            }
        }
        this.state.loading = false;
    }

    async _reload() {
        const keepIdx = this.state.idx;
        await this._load();
        this.state.idx = Math.min(
            keepIdx,
            Math.max(0, this.state.verticals.length - 1)
        );
    }

    // ── изгледи/навигация ──────────────────────────────────────────
    get total() {
        return this.state.verticals.length;
    }
    get current() {
        return this.state.verticals[this.state.idx] || null;
    }
    get currentSteps() {
        const v = this.current;
        return (v && this.state.steps[v.id]) || [];
    }
    get currentChapter() {
        const v = this.current;
        return chapterFor(v ? v.code : "");
    }
    get canNext() {
        const v = this.current;
        return !!(v && v.done);
    }
    get isLast() {
        return this.state.idx >= this.total - 1;
    }
    get progressPct() {
        if (!this.total) {
            return 0;
        }
        const done = this.state.verticals.filter((v) => v.done).length;
        return Math.round((done / this.total) * 100);
    }

    begin() {
        this.state.phase = "chapter";
        this.state.idx = 0;
        this._maybeAutoInstall();
    }
    back() {
        if (this.state.idx > 0) {
            this.state.idx -= 1;
            this._maybeAutoInstall();
        }
    }
    next() {
        if (!this.canNext) {
            return;
        }
        if (this.isLast) {
            this.state.phase = "finale";
            return;
        }
        this.state.idx += 1;
        this._maybeAutoInstall();
    }
    skip() {
        if (this.isLast) {
            this.state.phase = "finale";
            return;
        }
        this.state.idx += 1;
        this._maybeAutoInstall();
    }
    finish() {
        browser.location.href = "/odoo";
    }

    // ── auto-progression: преминава V0 → последна, auto-completing
    // required steps без user click. Optional остават за user.
    //
    // Per vertical:
    //  1. Required install_module → action_install
    //  2. Required checkpoint с registry_fetch=True + знаем VAT →
    //     vertical.wizard.action_registry_fetch (fetch от Търговския
    //     регистър; mark done auto)
    //  3. Други required checkpoint → action_mark_done (user-ите ги
    //     преглеждат в Settings → l10n.bg.vertical UI след wizard-а)
    //  4. Required config_action → НЕ auto (изисква user input в
    //     отделен form/wizard); wizard спира, user натиска Next ръчно
    //  5. Ako canNext → recurse в следващ vertical
    async _maybeAutoInstall() {
        if (this.state.busy) {
            return;
        }
        const v = this.current;
        if (!v) {
            return;
        }
        this.state.busy = true;
        this.state.error = "";
        let didSomething = false;
        try {
            // 1. install_module required
            const installs = (this.state.steps[v.id] || []).filter(
                (s) =>
                    s.step_type === "install_module" &&
                    !s.optional &&
                    !s.done &&
                    !["auto", "unavailable"].includes(s.state)
            );
            for (const step of installs) {
                await this.orm.call(
                    "l10n.bg.vertical.step",
                    "action_install",
                    [[step.id]]
                );
                didSomething = true;
            }
            if (installs.length) {
                await this._reload();
            }

            // 2. Trade Register fetch (registry_fetch=True + знаем VAT)
            const fresh = this.state.steps[v.id] || [];
            const regStep = fresh.find(
                (s) => s.registry_fetch && !s.done && !s.optional
            );
            if (regStep && this.state.vatEik) {
                const wizId = await this.orm.create(
                    "l10n.bg.vertical.wizard",
                    [
                        {
                            vertical_id: v.id,
                            registry_vat_eik: this.state.vatEik,
                        },
                    ]
                );
                await this.orm.call(
                    "l10n.bg.vertical.wizard",
                    "action_registry_fetch",
                    [[wizId]]
                );
                await this._reload();
                didSomething = true;
            }

            // 3. Други required checkpoint → mark done
            const checkpoints = (this.state.steps[v.id] || []).filter(
                (s) =>
                    s.step_type === "checkpoint" &&
                    !s.optional &&
                    !s.done &&
                    !s.registry_fetch &&
                    !["auto", "unavailable"].includes(s.state)
            );
            for (const step of checkpoints) {
                await this.orm.call(
                    "l10n.bg.vertical.step",
                    "action_mark_done",
                    [[step.id]]
                );
                didSomething = true;
            }
            if (checkpoints.length) {
                await this._reload();
            }

            // 4. Auto next ако vertical е done. Recurse за следващ.
            if (this.canNext && !this.isLast) {
                this.state.idx += 1;
                this.state.busy = false;
                // микро пауза за UI visual feedback (картинките да се
                // обновят преди да пуснем следваща глава)
                await new Promise((r) => setTimeout(r, 400));
                return this._maybeAutoInstall();
            }
            if (this.canNext && this.isLast) {
                this.state.phase = "finale";
            }
        } catch (e) {
            this.state.error =
                (e && e.data && e.data.message) ||
                (e && e.message) ||
                "Auto-install failed.";
        } finally {
            this.state.busy = false;
        }
        // eslint-disable-next-line no-unused-vars
        void didSomething;
    }

    // ── действия по стъпки (минават през backend методите) ─────────
    async _run(fn) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        this.state.error = "";
        try {
            await fn();
            await this._reload();
        } catch (e) {
            this.state.error =
                (e && e.data && e.data.message) ||
                (e && e.message) ||
                "Operation failed.";
        } finally {
            this.state.busy = false;
        }
    }
    installStep(step) {
        return this._run(() =>
            this.orm.call("l10n.bg.vertical.step", "action_install", [
                [step.id],
            ])
        );
    }
    markDone(step) {
        return this._run(() =>
            this.orm.call("l10n.bg.vertical.step", "action_mark_done", [
                [step.id],
            ])
        );
    }
    resetStep(step) {
        return this._run(() =>
            this.orm.call("l10n.bg.vertical.step", "action_reset", [
                [step.id],
            ])
        );
    }
    openConfig(step) {
        return this._run(() =>
            this.orm.call("l10n.bg.vertical.step", "action_open_config", [
                [step.id],
            ])
        );
    }
    tradeRegister() {
        const v = this.current;
        if (!v || !this.state.vatEik.trim()) {
            this.state.error = "Enter a VAT number or UIC first.";
            return;
        }
        return this._run(async () => {
            const wizId = await this.orm.create("l10n.bg.vertical.wizard", [
                { vertical_id: v.id, registry_vat_eik: this.state.vatEik },
            ]);
            await this.orm.call(
                "l10n.bg.vertical.wizard",
                "action_registry_fetch",
                [[wizId]]
            );
        });
    }

    // ── сцена (Lottie/SVG) ─────────────────────────────────────────
    _destroyScene() {
        if (this._scene) {
            this._scene.destroy();
            this._scene = null;
            this._sceneKey = null;
        }
    }
    async _syncScene() {
        if (this.state.phase !== "chapter") {
            this._destroyScene();
            return;
        }
        const v = this.current;
        const key = v ? v.code : "";
        if (!this.sceneRef.el || key === this._sceneKey) {
            return;
        }
        this._destroyScene();
        this._sceneKey = key;
        this._scene = await mountScene(this.sceneRef.el, this.currentChapter);
    }
}

registry.category("actions").add("l10n_bg_onboarding.app", OnboardingApp);
