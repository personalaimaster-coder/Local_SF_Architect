import * as fs from "node:fs";
import * as path from "node:path";
import { parse as parseJsonc } from "jsonc-parser";
import { log } from "./log";

/** Parse a JSON/JSONC file, returning {} for missing or empty files. */
export function readJsonc(filePath: string): Record<string, any> {
  if (!fs.existsSync(filePath)) {
    return {};
  }
  const raw = fs.readFileSync(filePath, "utf8").trim();
  if (!raw) {
    return {};
  }
  const errors: any[] = [];
  const parsed = parseJsonc(raw, errors, { allowTrailingComma: true });
  if (errors.length > 0) {
    log(`warning: ${errors.length} parse issue(s) in ${filePath}; proceeding with best-effort parse.`);
  }
  return parsed && typeof parsed === "object" ? parsed : {};
}

/** Copy an existing file to a timestamped `.bak` next to it. No-op if absent. */
export function backupFile(filePath: string): void {
  if (!fs.existsSync(filePath)) {
    return;
  }
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const backup = `${filePath}.${stamp}.bak`;
  fs.copyFileSync(filePath, backup);
  log(`backed up ${filePath} -> ${backup}`);
}

/** Write an object as pretty-printed JSON, creating parent dirs as needed. */
export function writeJson(filePath: string, data: unknown): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n", "utf8");
  log(`wrote ${filePath}`);
}

/**
 * Idempotently merge a single MCP server entry into a config file under
 * `rootKey` (e.g. "mcpServers" or "servers"). Existing servers are preserved.
 * Returns true if the file was changed.
 */
export function mergeServerEntry(
  filePath: string,
  rootKey: string,
  serverKey: string,
  entry: Record<string, unknown>
): boolean {
  const current = readJsonc(filePath);
  const servers = (current[rootKey] && typeof current[rootKey] === "object"
    ? current[rootKey]
    : {}) as Record<string, unknown>;

  const existing = servers[serverKey];
  if (existing && JSON.stringify(existing) === JSON.stringify(entry)) {
    log(`${serverKey} already present and unchanged in ${filePath}.`);
    return false;
  }

  backupFile(filePath);
  servers[serverKey] = entry;
  current[rootKey] = servers;
  writeJson(filePath, current);
  return true;
}
