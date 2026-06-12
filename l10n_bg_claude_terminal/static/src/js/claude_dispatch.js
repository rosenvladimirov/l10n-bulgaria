/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
//
// Генеричен AI dispatch грид — показва се от list/kanban „AI MCP" бутона на
// ВСЕКИ модел. Винаги има Terminal + Ask me; модул-специфични skills се
// регистрират през claudeDispatchProviders registry (напр. account.move
// skills идват от l10n_bg_ai_invoice_glue). Преди това гридът живееше в
// invoice_glue и се показваше само за account.move — затова липсваше другаде.

import { Component, useState, markup } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// Registry за модул-специфични skill provider-и.
//   register(model, { getSkills(ids, env) -> [{key,label,icon}],
//                     runSkill(key, ids, env, addLog, setResult) })
export const claudeDispatchProviders = registry.category("claude_dispatch_providers");

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

export class ClaudeDispatchDialog extends Component {
    static template = "l10n_bg_claude_terminal.ClaudeDispatchDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        skills: { type: Array, optional: true },
        onTerminal: Function,
        onAsk: { type: Function, optional: true },
        onSkill: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({
            phase: "pick",
            log: [],
            error: null,
            activeSkillLabel: "",
            resultHtml: null,
        });
    }

    get skills() { return this.props.skills || []; }

    clickTerminal() {
        this.props.close();
        this.props.onTerminal();
    }

    clickAsk() {
        // Отваря терминала в ask режим за текущия запис; ако няма handler
        // (без record контекст) → обикновен терминал.
        this.props.close();
        if (this.props.onAsk) {
            this.props.onAsk();
        } else {
            this.props.onTerminal();
        }
    }

    async clickSkill(skill) {
        if (!this.props.onSkill) {
            this.props.close();
            this.props.onTerminal();
            return;
        }
        this.state.phase = "running";
        this.state.activeSkillLabel = skill.label;
        this.state.log = [];
        this.state.error = null;
        this.state.resultHtml = null;
        const addLog = (line) => this.state.log.push(line);
        const setResult = (html) => { this.state.resultHtml = markup(html); };
        try {
            await this.props.onSkill(skill.key, addLog, setResult);
            this.state.phase = "done";
        } catch (e) {
            this.state.error = e.data?.message || e.message || String(e);
            this.state.phase = "error";
        }
    }

    backToPick() {
        this.state.phase = "pick";
        this.state.log = [];
        this.state.error = null;
        this.state.resultHtml = null;
    }
}

/**
 * Показва генеричния dispatch грид. openTerminal се подава от извикващия
 * (terminal_listview/kanbanview) за да няма кръгов import с ClaudeTerminalDialog.
 *
 * @param {Object} dialogService
 * @param {Object} ctx - {resModel, ids, env, openTerminal(focus)}
 */
export async function showClaudeDispatch(dialogService, ctx) {
    const { resModel, ids, env, openTerminal } = ctx;
    const provider = claudeDispatchProviders.get(resModel, null);

    let skills = [];
    if (provider && provider.getSkills) {
        try {
            skills = (await provider.getSkills(ids, env)) || [];
        } catch { skills = []; }
    }

    dialogService.add(ClaudeDispatchDialog, {
        skills,
        onTerminal: () => openTerminal(""),
        onAsk: () => openTerminal("ask"),
        onSkill: provider && provider.runSkill
            ? async (key, addLog, setResult) => {
                  if (!ids.length) { openTerminal(""); return; }
                  await provider.runSkill(key, ids, env, addLog, setResult);
                  await sleep(80);
                  env.bus.trigger("CLAUDE_REFRESH", { model: resModel });
              }
            : undefined,
    });
}

export { _t };
