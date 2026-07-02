import * as vscode from "vscode";
import { findUv, installEngine, isEngineInstalled, runCli, getEnginePackage } from "./engine";
import { log, logError, show as showLogs } from "./log";
import { DOCS_UV_INSTALL, EXTENSION_ID, STATE_SETUP_COMPLETE } from "./constants";

function config() {
  return vscode.workspace.getConfiguration(EXTENSION_ID);
}

/**
 * Ensure `uv` is available. If not, guide the user to install it (we never
 * silently pipe a remote script to a shell). Returns the uv path or null.
 */
export async function ensureUv(): Promise<string | null> {
  const uv = await findUv();
  if (uv) {
    log(`using uv at: ${uv}`);
    return uv;
  }

  const choice = await vscode.window.showErrorMessage(
    "Local SF Architect needs the `uv` package manager, which was not found. " +
      "Install it, then retry.",
    "Open Install Guide",
    "Retry"
  );
  if (choice === "Open Install Guide") {
    await vscode.env.openExternal(vscode.Uri.parse(DOCS_UV_INSTALL));
    return null;
  }
  if (choice === "Retry") {
    return findUv();
  }
  return null;
}

/** Ensure the engine package is installed, installing it with a progress UI. */
export async function ensureEngineInstalled(uvPath: string): Promise<boolean> {
  if (await isEngineInstalled(uvPath)) {
    log("engine already installed.");
    return true;
  }
  return installEngineWithProgress(uvPath);
}

export async function installEngineWithProgress(uvPath: string): Promise<boolean> {
  return vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: `Installing ${getEnginePackage()}…`,
      cancellable: true,
    },
    async (progress, token) => {
      const controller = new AbortController();
      token.onCancellationRequested(() => controller.abort());
      try {
        await installEngine(uvPath, {
          signal: controller.signal,
          onData: (chunk) => {
            log(chunk.trimEnd());
            const line = chunk.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).pop();
            if (line) {
              progress.report({ message: line.slice(0, 80) });
            }
          },
        });
        log("engine installed.");
        return true;
      } catch (err) {
        logError("engine install failed", err);
        const pick = await vscode.window.showErrorMessage(
          "Failed to install the Local SF Architect engine.",
          "Show Logs"
        );
        if (pick === "Show Logs") {
          showLogs();
        }
        return false;
      }
    }
  );
}

/**
 * Download the embedding model (optional, ~130 MB) and seed the knowledge base.
 * Marks setup complete in globalState on success.
 */
export async function runFirstRunSetup(
  uvPath: string,
  context: vscode.ExtensionContext
): Promise<boolean> {
  const downloadModel = config().get<boolean>("autoDownloadModel", true);

  return vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Local SF Architect: first-time setup",
      cancellable: true,
    },
    async (progress, token) => {
      const controller = new AbortController();
      token.onCancellationRequested(() => controller.abort());
      const stream = (chunk: string) => log(chunk.trimEnd());

      try {
        if (downloadModel) {
          progress.report({ message: "Downloading embedding model (~130 MB, one time)…" });
          const code = await runCli(uvPath, ["doctor", "--download"], {
            signal: controller.signal,
            onData: stream,
          });
          if (code !== 0) {
            throw new Error(`doctor --download exited ${code}`);
          }
        }

        progress.report({ message: "Seeding governor limits + architecture patterns…" });
        const seedCode = await runCli(uvPath, ["seed"], {
          signal: controller.signal,
          onData: stream,
        });
        if (seedCode !== 0) {
          throw new Error(`seed exited ${seedCode}`);
        }

        await context.globalState.update(STATE_SETUP_COMPLETE, true);
        log("first-run setup complete.");
        return true;
      } catch (err) {
        logError("first-run setup failed", err);
        const pick = await vscode.window.showErrorMessage(
          "Local SF Architect setup failed. The knowledge base may be incomplete.",
          "Show Logs",
          "Retry"
        );
        if (pick === "Show Logs") {
          showLogs();
        } else if (pick === "Retry") {
          return runFirstRunSetup(uvPath, context);
        }
        return false;
      }
    }
  );
}

/** Drop and rebuild the local stores (recovery path after a schema change). */
export async function rebuildStores(uvPath: string): Promise<boolean> {
  return vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Local SF Architect: rebuilding local stores…",
      cancellable: false,
    },
    async () => {
      try {
        const code = await runCli(uvPath, ["rebuild"], { onData: (c) => log(c.trimEnd()) });
        if (code !== 0) {
          throw new Error(`rebuild exited ${code}`);
        }
        vscode.window.showInformationMessage("Local SF Architect: stores rebuilt.");
        return true;
      } catch (err) {
        logError("rebuild failed", err);
        vscode.window.showErrorMessage("Local SF Architect: rebuild failed. See logs.");
        return false;
      }
    }
  );
}
