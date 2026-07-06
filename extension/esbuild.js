// Bundles the extension into a single dist/extension.js file.
const esbuild = require("esbuild");

const production = process.argv.includes("--production");
const watch = process.argv.includes("--watch");

async function main() {
  const ctx = await esbuild.context({
    entryPoints: ["src/extension.ts"],
    bundle: true,
    format: "cjs",
    minify: production,
    sourcemap: !production,
    sourcesContent: false,
    platform: "node",
    target: "node20",
    outfile: "dist/extension.js",
    // Prefer each dependency's ESM entry (`module`) over its `main`. Some deps
    // (e.g. jsonc-parser) ship a UMD `main` whose dynamic `require('./impl/..')`
    // esbuild can't statically follow — leaving broken runtime requires that
    // crash activation. The ESM build bundles cleanly.
    mainFields: ["module", "main"],
    // `vscode` is provided by the host at runtime and must never be bundled.
    external: ["vscode"],
    logLevel: "info",
  });

  if (watch) {
    await ctx.watch();
  } else {
    await ctx.rebuild();
    await ctx.dispose();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
