import { spawn } from "node:child_process";
import * as os from "node:os";
import { log } from "./log";

export interface ExecResult {
  code: number | null;
  stdout: string;
  stderr: string;
}

export interface ExecOptions {
  cwd?: string;
  env?: NodeJS.ProcessEnv;
  /** Called with each chunk of combined stdout/stderr as it streams. */
  onData?: (chunk: string) => void;
  /** Abort signal to cancel the process. */
  signal?: AbortSignal;
}

/**
 * Run a command and capture its output. Never rejects on a non-zero exit code —
 * the caller inspects `result.code`. Rejects only if the process cannot be
 * spawned at all (e.g. command not found).
 */
export function exec(command: string, args: string[], options: ExecOptions = {}): Promise<ExecResult> {
  return new Promise((resolve, reject) => {
    log(`exec: ${command} ${args.join(" ")}`);
    const child = spawn(command, args, {
      cwd: options.cwd,
      env: options.env ?? process.env,
      signal: options.signal,
      shell: false,
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (d: Buffer) => {
      const s = d.toString();
      stdout += s;
      options.onData?.(s);
    });
    child.stderr.on("data", (d: Buffer) => {
      const s = d.toString();
      stderr += s;
      options.onData?.(s);
    });

    child.on("error", (err) => reject(err));
    child.on("close", (code) => resolve({ code, stdout, stderr }));
  });
}

/**
 * Resolve the absolute path of an executable on PATH using the platform's
 * locator (`which` on POSIX, `where` on Windows). Returns null if not found.
 */
export async function which(name: string): Promise<string | null> {
  const isWin = os.platform() === "win32";
  const locator = isWin ? "where" : "which";
  try {
    const res = await exec(locator, [name]);
    if (res.code !== 0) {
      return null;
    }
    const first = res.stdout.split(/\r?\n/).map((l) => l.trim()).find(Boolean);
    return first ?? null;
  } catch {
    return null;
  }
}
