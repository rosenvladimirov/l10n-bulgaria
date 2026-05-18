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
    }
    back() {
        if (this.state.idx > 0) {
            this.state.idx -= 1;
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
    }
    skip() {
        if (this.isLast) {
            this.state.phase = "finale";
            return;
        }
        this.state.idx += 1;
    }
    finish() {
        browser.location.href = "/odoo";
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
