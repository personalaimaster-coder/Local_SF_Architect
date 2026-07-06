import * as vscode from "vscode";
import * as path from "node:path";
import { findUv, resolveMcpCommand, isEngineInstalled } from "../engine";
import { mergeServerEntry } from "../jsonConfig";
import { log, logError } from "../log";
import { MCP_PROVIDER_ID, SERVER_KEY, SERVER_LABEL } from "../constants";

const didChangeEmitter = new vscode.EventEmitter<void>();

/** Re-query: tells VS Code to refresh our MCP server definitions. */
export function refreshVsCodeMcp(): void {
  didChangeEmitter.fire();
}

/**
 * Register the native VS Code MCP server definition provider (VS Code 1.101+).
 * Returns true if the API was available and the provider was registered.
 */
export function registerMcpProvider(context: vscode.ExtensionContext): boolean {
  const lm = (vscode as any).lm;
  const StdioDef = (vscode as any).McpStdioServerDefinition;
  if (typeof lm?.registerMcpServerDefinitionProvider !== "function" || typeof StdioDef !== "function") {
    log("native MCP provider API unavailable on this host.");
    return false;
  }

  const disposable = lm.registerMcpServerDefinitionProvider(MCP_PROVIDER_ID, {
    onDidChangeMcpServerDefinitions: didChangeEmitter.event,
    provideMcpServerDefinitions: async () => {
      try {
        const uv = await findUv();
        if (!uv) {
          log("provideMcpServerDefinitions: uv not found; no server offered yet.");
          return [];
        }
        if (!(await isEngineInstalled(uv))) {
          log("provideMcpServerDefinitions: engine not installed yet; no server offered.");
          return [];
        }
        const cmd = await resolveMcpCommand(uv);
        log(`provideMcpServerDefinitions: ${cmd.command} ${cmd.args.join(" ")}`);
        return [new StdioDef(SERVER_LABEL, cmd.command, cmd.args)];
      } catch (err) {
        logError("provideMcpServerDefinitions failed", err);
        return [];
      }
    },
    resolveMcpServerDefinition: async (server: unknown) => server,
  });

  context.subscriptions.push(disposable);
  log("registered native VS Code MCP provider.");
  return true;
}

/**
 * Fallback for hosts without the provider API: write the server into the
 * workspace `.vscode/mcp.json` (VS Code uses the `servers` root key).
 * Returns true if a config was written.
 */
export async function writeWorkspaceMcpJson(): Promise<boolean> {
  const folder = vscode.workspace.workspaceFolders?.[0];
  if (!folder) {
    vscode.window.showWarningMessage(
      "Local SF Architect: open a folder to write the VS Code MCP config (.vscode/mcp.json)."
    );
    return false;
  }
  const uv = await findUv();
  if (!uv) {
    return false;
  }
  const cmd = await resolveMcpCommand(uv);
  const target = path.join(folder.uri.fsPath, ".vscode", "mcp.json");
  const changed = mergeServerEntry(target, "servers", SERVER_KEY, {
    type: "stdio",
    command: cmd.command,
    args: cmd.args,
  });
  if (changed) {
    log(`wrote VS Code MCP fallback config to ${target}`);
  }
  return true;
}
