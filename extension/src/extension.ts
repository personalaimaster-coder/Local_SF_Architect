import * as vscode from "vscode";
import { detectHost, detectAgents, type AgentDetection } from "./detect";
import { findUv } from "./engine";
import {
  ensureUv,
  ensureEngineInstalled,
  installEngineWithProgress,
  runFirstRunSetup,
  rebuildStores,
} from "./setup";
import { registerMcpProvider, refreshVsCodeMcp, writeWorkspaceMcpJson } from "./wiring/vscode";
import { configureCursor } from "./wiring/cursor";
import { configureClaudeCode } from "./wiring/claudeCode";
import { initStatusBar, setState } from "./statusBar";
import { log, logError, show as showLogs } from "./log";
import { EXTENSION_ID, STATE_INSTALL_PROMPTED, STATE_SETUP_COMPLETE } from "./constants";

let providerRegistered = false;

export function activate(context: vscode.ExtensionContext): void {
  log("Local SF Architect extension activating.");

  // Register commands FIRST so they are always available, even if a later
  // step throws. Otherwise a failure below would leave every command
  // unregistered ("command 'sfArchitect.*' not found").
  registerCommands(context);

  try {
    initStatusBar(context);
  } catch (err) {
    logError("initStatusBar failed", err);
  }

  // Register the native MCP provider as early as possible so Copilot can pick
  // up the server once the engine is installed (the provider returns nothing
  // until then, and we fire a refresh after install/configure).
  try {
    providerRegistered = registerMcpProvider(context);
  } catch (err) {
    logError("registerMcpProvider failed", err);
    providerRegistered = false;
  }

  void reflectInstalledState();

  if (config().get<boolean>("autoSetupOnActivate", true)) {
    void maybeAutoSetup(context);
  }
}

export function deactivate(): void {
  /* OutputChannel + status bar disposed via context.subscriptions. */
}

function config() {
  return vscode.workspace.getConfiguration(EXTENSION_ID);
}

function registerCommands(context: vscode.ExtensionContext): void {
  const reg = (id: string, fn: (...args: any[]) => any) =>
    context.subscriptions.push(vscode.commands.registerCommand(id, fn));

  reg("sfArchitect.setup", () => runFullSetup(context));
  reg("sfArchitect.installEngine", () => installCommand());
  reg("sfArchitect.firstRunSetup", () => firstRunCommand(context));
  reg("sfArchitect.configureCopilot", () => configureCopilotCommand());
  reg("sfArchitect.configureCursor", () => withResult("Cursor", configureCursor()));
  reg("sfArchitect.configureClaudeCode", () => withResult("Claude Code", configureClaudeCode()));
  reg("sfArchitect.configureAll", () => configureAllCommand());
  reg("sfArchitect.rebuildStores", () => rebuildCommand());
  reg("sfArchitect.showLogs", () => showLogs());
  reg("sfArchitect.showStatus", () => showStatusCommand(context));
}

async function withResult(label: string, work: Promise<boolean>): Promise<void> {
  const ok = await work;
  if (ok) {
    vscode.window.showInformationMessage(`Local SF Architect: ${label} configured.`);
  } else {
    vscode.window.showWarningMessage(`Local SF Architect: could not configure ${label}. See logs.`);
  }
}

/** Update the status bar based on whether uv + engine appear installed. */
async function reflectInstalledState(): Promise<void> {
  const uv = await findUv();
  if (!uv) {
    setState("missing");
    return;
  }
  const { isEngineInstalled } = await import("./engine");
  setState((await isEngineInstalled(uv)) ? "ready" : "missing");
}

/** First-activation flow: confirm, then install + seed + configure everything. */
async function maybeAutoSetup(context: vscode.ExtensionContext): Promise<void> {
  if (context.globalState.get<boolean>(STATE_INSTALL_PROMPTED)) {
    return;
  }
  await context.globalState.update(STATE_INSTALL_PROMPTED, true);

  const choice = await vscode.window.showInformationMessage(
    "Local SF Architect can install its offline engine and wire it into your AI agents (Copilot, Cursor, Claude Code). Set up now?",
    "Set up now",
    "Later"
  );
  if (choice === "Set up now") {
    await runFullSetup(context);
  }
}

async function runFullSetup(context: vscode.ExtensionContext): Promise<void> {
  setState("installing");
  const uv = await ensureUv();
  if (!uv) {
    setState("missing");
    return;
  }

  if (!(await ensureEngineInstalled(uv))) {
    setState("error");
    return;
  }
  refreshVsCodeMcp();

  if (!context.globalState.get<boolean>(STATE_SETUP_COMPLETE)) {
    const ok = await runFirstRunSetup(uv, context);
    if (!ok) {
      setState("error");
      return;
    }
  }

  if (!config().get<boolean>("autoConfigureAgents", true)) {
    refreshVsCodeMcp();
    setState("ready");
    const pick = await vscode.window.showInformationMessage(
      "Local SF Architect engine is ready. Auto-configure is disabled — wire it into your agents when ready.",
      "Configure All Agents"
    );
    if (pick === "Configure All Agents") {
      await configureAllCommand();
    }
    return;
  }

  const agents = await configureDetectedAgents();
  refreshVsCodeMcp();
  setState("ready", agents);
  vscode.window.showInformationMessage(
    agents.length
      ? `Local SF Architect is ready and wired to: ${agents.join(", ")}.`
      : "Local SF Architect is installed. Open a folder or install a supported agent to wire it up."
  );
}

async function installCommand(): Promise<void> {
  setState("installing");
  const uv = await ensureUv();
  if (!uv) {
    setState("missing");
    return;
  }
  const ok = await installEngineWithProgress(uv);
  if (ok) {
    refreshVsCodeMcp();
    setState("ready");
    vscode.window.showInformationMessage("Local SF Architect: engine installed.");
  } else {
    setState("error");
  }
}

async function firstRunCommand(context: vscode.ExtensionContext): Promise<void> {
  const uv = await ensureUv();
  if (!uv) {
    return;
  }
  if (!(await ensureEngineInstalled(uv))) {
    return;
  }
  const ok = await runFirstRunSetup(uv, context);
  if (ok) {
    refreshVsCodeMcp();
    vscode.window.showInformationMessage("Local SF Architect: model + knowledge base ready.");
  }
}

async function configureCopilotCommand(): Promise<void> {
  if (providerRegistered) {
    refreshVsCodeMcp();
    vscode.window.showInformationMessage(
      "Local SF Architect: registered with VS Code. Open Copilot Chat in Agent mode to use it."
    );
    return;
  }
  await withResult("VS Code (mcp.json)", writeWorkspaceMcpJson());
}

/** Configure whichever agents are present on this host. Returns their labels. */
async function configureDetectedAgents(): Promise<string[]> {
  const host = detectHost();
  const agents = await detectAgents(host);
  return applyAgentConfig(host.isCursor, agents);
}

async function applyAgentConfig(isCursor: boolean, agents: AgentDetection): Promise<string[]> {
  const configured: string[] = [];

  if (agents.copilot) {
    if (providerRegistered) {
      refreshVsCodeMcp();
      configured.push("Copilot");
    } else if (await writeWorkspaceMcpJson()) {
      configured.push("VS Code");
    }
  }

  if (agents.cursor && (await configureCursor())) {
    configured.push("Cursor");
  }

  if (agents.claudeCode && (await configureClaudeCode(agents.claudeCli ?? undefined))) {
    configured.push("Claude Code");
  }

  // In Cursor with the Claude CLI also present, both get wired — that's intended.
  void isCursor;
  return configured;
}

async function configureAllCommand(): Promise<void> {
  const agents = await configureDetectedAgents();
  refreshVsCodeMcp();
  if (agents.length) {
    setState("ready", agents);
    vscode.window.showInformationMessage(`Local SF Architect wired to: ${agents.join(", ")}.`);
  } else {
    vscode.window.showWarningMessage(
      "Local SF Architect: no supported agents detected. Install GitHub Copilot, run inside Cursor, or install the Claude Code CLI."
    );
  }
}

async function rebuildCommand(): Promise<void> {
  const uv = await ensureUv();
  if (!uv) {
    return;
  }
  await rebuildStores(uv);
}

async function showStatusCommand(context: vscode.ExtensionContext): Promise<void> {
  const host = detectHost();
  const agents = await detectAgents(host);
  const uv = await findUv();
  const { isEngineInstalled } = await import("./engine");
  const engineReady = uv ? await isEngineInstalled(uv) : false;
  const setupDone = context.globalState.get<boolean>(STATE_SETUP_COMPLETE) === true;

  const lines = [
    `Host: ${host.appName}${host.isCursor ? " (Cursor)" : ""}`,
    `uv: ${uv ?? "not found"}`,
    `Engine installed: ${engineReady ? "yes" : "no"}`,
    `Model + knowledge base seeded: ${setupDone ? "yes" : "no"}`,
    `Native MCP provider API: ${host.hasMcpProviderApi ? "available" : "unavailable"}`,
    `Detected agents: ${
      [
        agents.copilot ? "Copilot/VS Code" : null,
        agents.cursor ? "Cursor" : null,
        agents.claudeCode ? "Claude Code" : null,
      ]
        .filter(Boolean)
        .join(", ") || "none"
    }`,
  ];

  const pick = await vscode.window.showInformationMessage(
    lines.join("\n"),
    { modal: true },
    "Run Setup",
    "Show Logs"
  );
  if (pick === "Run Setup") {
    await runFullSetup(context);
  } else if (pick === "Show Logs") {
    showLogs();
  }
}
