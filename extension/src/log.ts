import * as vscode from "vscode";

let channel: vscode.OutputChannel | undefined;

export function getOutputChannel(): vscode.OutputChannel {
  if (!channel) {
    channel = vscode.window.createOutputChannel("Local SF Architect");
  }
  return channel;
}

function stamp(): string {
  return new Date().toISOString();
}

export function log(message: string): void {
  getOutputChannel().appendLine(`[${stamp()}] ${message}`);
}

export function logError(message: string, err?: unknown): void {
  const detail = err instanceof Error ? `${err.message}` : err ? String(err) : "";
  getOutputChannel().appendLine(`[${stamp()}] ERROR: ${message}${detail ? ` — ${detail}` : ""}`);
}

export function show(): void {
  getOutputChannel().show(true);
}

export function dispose(): void {
  channel?.dispose();
  channel = undefined;
}
