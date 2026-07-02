import * as os from "node:os";
import * as path from "node:path";
import { findUv, resolveMcpCommand } from "../engine";
import { mergeServerEntry } from "../jsonConfig";
import { log } from "../log";
import { SERVER_KEY, type EngineCommand } from "../constants";

/** Path to Cursor's user-level MCP config. */
export function cursorConfigPath(): string {
  return path.join(os.homedir(), ".cursor", "mcp.json");
}

function buildEntry(cmd: EngineCommand): Record<string, unknown> {
  // Cursor uses the same shape as Claude Desktop: command + args (+ optional env).
  return { command: cmd.command, args: cmd.args };
}

/**
 * Wire the engine into Cursor by merging into `~/.cursor/mcp.json` under the
 * `mcpServers` key. Existing servers are preserved; the prior file is backed up.
 * Returns true on success.
 */
export async function configureCursor(): Promise<boolean> {
  const uv = await findUv();
  if (!uv) {
    log("configureCursor: uv not found; skipping.");
    return false;
  }
  const cmd = await resolveMcpCommand(uv);
  const target = cursorConfigPath();
  const changed = mergeServerEntry(target, "mcpServers", SERVER_KEY, buildEntry(cmd));
  log(changed ? `Cursor config updated: ${target}` : `Cursor config already up to date: ${target}`);
  return true;
}
