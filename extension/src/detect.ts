import * as vscode from "vscode";
import { exec, which } from "./proc";
import { log } from "./log";

export interface HostInfo {
  /** True when running inside Cursor (a VS Code fork) rather than vanilla VS Code. */
  isCursor: boolean;
  /** True when the GitHub Copilot Chat extension is installed (VS Code MCP host). */
  hasCopilotChat: boolean;
  /** True when this build exposes the native MCP server definition provider API. */
  hasMcpProviderApi: boolean;
  appName: string;
}

export interface AgentDetection {
  /** Configure VS Code/Copilot natively (only meaningful in non-Cursor VS Code). */
  copilot: boolean;
  /** Configure Cursor by writing its MCP config. */
  cursor: boolean;
  /** Configure Claude Code via its CLI. */
  claudeCode: boolean;
  claudeCli: string | null;
}

export function detectHost(): HostInfo {
  const appName = vscode.env.appName ?? "";
  const isCursor =
    /cursor/i.test(appName) || /cursor/i.test((vscode.env as any).appHost ?? "");
  const hasCopilotChat =
    !!vscode.extensions.getExtension("GitHub.copilot-chat") ||
    !!vscode.extensions.getExtension("GitHub.copilot");
  // The provider API landed in VS Code 1.101. Feature-detect rather than trust
  // the version string, since forks report their own versions.
  const hasMcpProviderApi =
    typeof (vscode as any).lm?.registerMcpServerDefinitionProvider === "function" &&
    typeof (vscode as any).McpStdioServerDefinition === "function";

  log(
    `host: appName="${appName}" isCursor=${isCursor} copilotChat=${hasCopilotChat} mcpProviderApi=${hasMcpProviderApi}`
  );
  return { isCursor, hasCopilotChat, hasMcpProviderApi, appName };
}

/** Locate the Claude Code CLI, returning its absolute path or null. */
export async function detectClaudeCli(): Promise<string | null> {
  const path = await which("claude");
  if (!path) {
    return null;
  }
  // Confirm it is actually the Claude Code CLI and responds.
  try {
    const res = await exec(path, ["--version"]);
    if (res.code === 0) {
      return path;
    }
  } catch {
    /* fall through */
  }
  return null;
}

/**
 * Decide which agents this machine can be wired to. In Cursor we target
 * Cursor's own config; in vanilla VS Code with Copilot we target the native MCP
 * host. Claude Code is configured whenever its CLI is present, on any host.
 */
export async function detectAgents(host: HostInfo): Promise<AgentDetection> {
  const claudeCli = await detectClaudeCli();
  return {
    cursor: host.isCursor,
    copilot: !host.isCursor && (host.hasMcpProviderApi || host.hasCopilotChat),
    claudeCode: claudeCli !== null,
    claudeCli,
  };
}
