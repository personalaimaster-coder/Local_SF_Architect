import * as vscode from "vscode";
import * as os from "node:os";
import * as path from "node:path";
import * as fs from "node:fs";
import { exec, which, type ExecOptions } from "./proc";
import { log, logError } from "./log";
import { CLI_SCRIPT, MCP_SCRIPT, EXTENSION_ID, type EngineCommand } from "./constants";

const isWin = os.platform() === "win32";

function config() {
  return vscode.workspace.getConfiguration(EXTENSION_ID);
}

export function getEnginePackage(): string {
  return config().get<string>("enginePackage")?.trim() || "sf-local-architect";
}

/**
 * Resolve the absolute path to the `uv` executable. Order: user setting, PATH,
 * then well-known install locations (uv's own installer and Homebrew/cargo).
 */
export async function findUv(): Promise<string | null> {
  const configured = config().get<string>("uvPath")?.trim();
  if (configured && fs.existsSync(configured)) {
    return configured;
  }

  const onPath = await which("uv");
  if (onPath) {
    return onPath;
  }

  const home = os.homedir();
  const candidates = isWin
    ? [
        path.join(home, ".local", "bin", "uv.exe"),
        path.join(home, ".cargo", "bin", "uv.exe"),
      ]
    : [
        path.join(home, ".local", "bin", "uv"),
        path.join(home, ".cargo", "bin", "uv"),
        "/opt/homebrew/bin/uv",
        "/usr/local/bin/uv",
      ];
  for (const c of candidates) {
    if (fs.existsSync(c)) {
      return c;
    }
  }
  return null;
}

/** True if the engine package is already installed as a uv tool. */
export async function isEngineInstalled(uvPath: string): Promise<boolean> {
  try {
    const res = await exec(uvPath, ["tool", "list"]);
    if (res.code !== 0) {
      return false;
    }
    return res.stdout.toLowerCase().includes(getEnginePackage().toLowerCase());
  } catch {
    return false;
  }
}

/** Install or upgrade the engine via `uv tool install --upgrade`. */
export async function installEngine(uvPath: string, options: ExecOptions = {}): Promise<void> {
  const pkg = getEnginePackage();
  log(`installing engine package: ${pkg}`);
  const res = await exec(uvPath, ["tool", "install", "--upgrade", pkg], options);
  if (res.code !== 0) {
    throw new Error(`uv tool install failed (exit ${res.code}). See logs for details.`);
  }
}

/** Resolve the bin directory that `uv tool` installs console scripts into. */
async function findToolBinDir(uvPath: string): Promise<string | null> {
  try {
    const res = await exec(uvPath, ["tool", "dir", "--bin"]);
    if (res.code === 0) {
      const dir = res.stdout.trim().split(/\r?\n/).pop()?.trim();
      if (dir && fs.existsSync(dir)) {
        return dir;
      }
    }
  } catch {
    /* older uv without `--bin`; fall through */
  }
  return null;
}

/** Resolve the absolute path of an installed console script, or null. */
async function resolveScript(uvPath: string, script: string): Promise<string | null> {
  const onPath = await which(script);
  if (onPath) {
    return onPath;
  }

  const binDir = await findToolBinDir(uvPath);
  const fileName = isWin ? `${script}.exe` : script;
  const searchDirs = [
    binDir,
    path.join(os.homedir(), ".local", "bin"),
  ].filter((d): d is string => !!d);

  for (const dir of searchDirs) {
    const candidate = path.join(dir, fileName);
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

/**
 * Build the command that launches the MCP server. Prefer the absolute path to
 * the installed shim (robust against minimal PATH when an editor spawns it);
 * fall back to `uv tool run` with an absolute uv path.
 */
export async function resolveMcpCommand(uvPath: string): Promise<EngineCommand> {
  const shim = await resolveScript(uvPath, MCP_SCRIPT);
  if (shim) {
    return { command: shim, args: [] };
  }
  log("MCP shim not found on disk; falling back to `uv tool run`.");
  return { command: uvPath, args: ["tool", "run", "--from", getEnginePackage(), MCP_SCRIPT] };
}

/** Build the command that runs a CLI subcommand (`doctor`, `seed`, ...). */
export async function resolveCliCommand(
  uvPath: string,
  subArgs: string[]
): Promise<EngineCommand> {
  const shim = await resolveScript(uvPath, CLI_SCRIPT);
  if (shim) {
    return { command: shim, args: subArgs };
  }
  return {
    command: uvPath,
    args: ["tool", "run", "--from", getEnginePackage(), CLI_SCRIPT, ...subArgs],
  };
}

/** Run a CLI subcommand, streaming output. Returns the exit code. */
export async function runCli(
  uvPath: string,
  subArgs: string[],
  options: ExecOptions = {}
): Promise<number | null> {
  const { command, args } = await resolveCliCommand(uvPath, subArgs);
  try {
    const res = await exec(command, args, options);
    return res.code;
  } catch (err) {
    logError(`failed to run CLI: ${CLI_SCRIPT} ${subArgs.join(" ")}`, err);
    throw err;
  }
}
