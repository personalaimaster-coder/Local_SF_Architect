import * as vscode from "vscode";

export type EngineState = "unknown" | "missing" | "installing" | "ready" | "error";

let item: vscode.StatusBarItem | undefined;

export function initStatusBar(context: vscode.ExtensionContext): void {
  item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  item.command = "sfArchitect.showStatus";
  context.subscriptions.push(item);
  setState("unknown");
  item.show();
}

export function setState(state: EngineState, agents: string[] = []): void {
  if (!item) {
    return;
  }
  switch (state) {
    case "installing":
      item.text = "$(sync~spin) SF Architect";
      item.tooltip = "Local SF Architect: setting up…";
      break;
    case "ready":
      item.text = "$(check) SF Architect";
      item.tooltip = agents.length
        ? `Local SF Architect ready (wired to ${agents.join(", ")})`
        : "Local SF Architect ready";
      break;
    case "missing":
      item.text = "$(cloud-download) SF Architect";
      item.tooltip = "Local SF Architect: not installed — click to set up";
      break;
    case "error":
      item.text = "$(error) SF Architect";
      item.tooltip = "Local SF Architect: error — click for status";
      break;
    default:
      item.text = "$(tools) SF Architect";
      item.tooltip = "Local SF Architect";
  }
}
