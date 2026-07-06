import * as os from "node:os";
import * as path from "node:path";
import { findUv, resolveMcpCommand } from "../engine";
import { exec, which } from "../proc";
import { mergeServerEntry } from "../jsonConfig";
import { log, logError } from "../log";
import { SERVER_KEY, type EngineCommand } from "../constants";

/** Path to Claude Code's user config (also holds user-scoped mcpServers). */
export function claudeConfigPath(): string {
  return path.join(os.homedir(), ".claude.json");
}

/**
 * Wire the engine into Claude Code. Preferred path uses the `claude` CLI
 * (`claude mcp add --scope user`), which is the supported, future-proof way.
 * Falls back to merging into `~/.claude.json` if the CLI write fails.
 * Returns true on success.
 */
export async function configureClaudeCode(claudeCliPath?: string): Promise<boolean> {
  const uv = await findUv();
  if (!uv) {
    log("configureClaudeCode: uv not found; skipping.");
    return false;
  }
  const cmd = await resolveMcpCommand(uv);
  const claude = claudeCliPath ?? (await which("claude"));

  if (claude && (await addViaCli(claude, cmd))) {
    return true;
  }

  log("configureClaudeCode: falling back to direct ~/.claude.json edit.");
  return writeClaudeJson(cmd);
}

async function addViaCli(claude: string, cmd: EngineCommand): Promise<boolean> {
  try {
    // Remove any prior entry so re-running is idempotent (ignore failures).
    await exec(claude, ["mcp", "remove", SERVER_KEY, "--scope", "user"]).catch(() => undefined);

    // `claude mcp add [opts] <name> -- <command> [args...]`
    const args = ["mcp", "add", "--scope", "user", SERVER_KEY, "--", cmd.command, ...cmd.args];
    const res = await exec(claude, args);
    if (res.code === 0) {
      log(`Claude Code configured via CLI: ${SERVER_KEY}`);
      return true;
    }
    logError(`claude mcp add exited ${res.code}`, res.stderr.trim());
    return false;
  } catch (err) {
    logError("claude mcp add failed to run", err);
    return false;
  }
}

function writeClaudeJson(cmd: EngineCommand): boolean {
  const target = claudeConfigPath();
  try {
    const changed = mergeServerEntry(target, "mcpServers", SERVER_KEY, {
      type: "stdio",
      command: cmd.command,
      args: cmd.args,
    });
    log(changed ? `Claude Code config updated: ${target}` : `Claude Code config already current.`);
    return true;
  } catch (err) {
    logError("failed to write ~/.claude.json", err);
    return false;
  }
}
