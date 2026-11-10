"use strict";

/**
 * Post-install script for the `apex-ai` npm package.
 *
 * Prepares the full APEX distribution in one shot so that `apex` can launch
 * the TUI immediately after `npm install -g apex-ai`:
 *   1. the verified native backend (`apex-rs`) in ~/.apex/bin
 *   2. the TUI frontend (Ink + React) in ~/.apex/tui-frontend
 *
 * Set APEX_SKIP_INSTALL=1 to skip all provisioning.
 */

const path = require("path");
const native = require("../lib/native");
const tui = require("../lib/tui");

async function main() {
  if (process.env.APEX_SKIP_INSTALL === "1") {
    console.log("[apex] postinstall skipped (APEX_SKIP_INSTALL=1)");
    return;
  }

  console.log("[apex] postinstall: provisioning native backend (apex-rs)…");
  try {
    const binary = await native.installNative({
      version: process.env.APEX_VERSION || "",
      env: process.env,
      log: (msg) => console.log("  " + msg),
    });
    console.log(`[apex] native backend ready: ${binary}`);
  } catch (err) {
    console.error(
      "[apex] postinstall: native backend provisioning failed: " + err.message
    );
    process.exit(1);
  }

  console.log("[apex] postinstall: preparing TUI frontend…");
  try {
    const dir = await tui.ensureTuiFrontend({
      env: process.env,
      log: (msg) => console.log("  " + msg),
    });
    console.log(`[apex] TUI frontend ready: ${dir}`);
  } catch (err) {
    console.error(
      "[apex] postinstall: TUI frontend provisioning failed: " + err.message
    );
    process.exit(1);
  }

  console.log(
    "[apex] postinstall: complete. Run 'apex' to start the TUI connected to the native backend."
  );
}

main().catch((err) => {
  console.error("[apex] postinstall: " + (err && err.message ? err.message : String(err)));
  process.exit(1);
});
