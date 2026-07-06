// Shared identifiers and labels used across the extension.

export const EXTENSION_ID = "sfArchitect";
export const MCP_PROVIDER_ID = "sfLocalArchitect.mcpProvider";

// The name the engine is registered under in every agent's MCP config.
export const SERVER_KEY = "sf-local-architect";
export const SERVER_LABEL = "Local SF Architect";

// Console scripts exposed by the Python package (see pyproject [project.scripts]).
export const MCP_SCRIPT = "sf-architect-mcp";
export const CLI_SCRIPT = "sf-architect";

// globalState keys.
export const STATE_SETUP_COMPLETE = "sfArchitect.setupComplete";
export const STATE_INSTALL_PROMPTED = "sfArchitect.installPrompted";

export const DOCS_UV_INSTALL = "https://docs.astral.sh/uv/getting-started/installation/";

export interface EngineCommand {
  command: string;
  args: string[];
}
