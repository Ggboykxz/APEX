#!/usr/bin/env node
"use strict";

/**
 * apex — npm wrapper for the APEX CLI.
 *
 * APEX is distributed through two channels only: this npm package and the
 * native Rust backend (`apex-rs`) published as GitHub Release assets. The
 * Python package is no longer published on PyPI, so the wrapper never tries
 * to provision it.
 *
 * Resolution order:
 *   1. APEX_BINARY env var (explicit override, always wins)
 *   2. a real `apex` executable already on PATH (source checkout, custom
 *      install)
 *   3. the native backend: `apex-rs` on PATH, the managed
 *      `~/.apex/bin/apex-rs`, or a checksum-verified download from the
 *      latest GitHub release
 *
 * The native backend is headless (`serve`, `run`, `tools`, …); install the
 * full TUI from a source checkout when you need it.
 *
 * Environment:
 *   APEX_BINARY        path to a pre-existing apex executable (override)
 *   APEX_VERSION       pin the release version (e.g. 0.1.0)
 *   APEX_INSTALL_METHOD `auto` (default) or `native`
 *   APEX_NATIVE        set to 0 to disable downloading the native backend
 *   APEX_SKIP_INSTALL  set to 1 to fail fast when apex is not found
 *   APEX_INSTALL_DIR   native backend install directory (default ~/.apex/bin)
 */

const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const https = require("https");
const resolver = require("../lib/resolver");
const native = require("../lib/native");
const tui = require("../lib/tui");

const SELF_REAL = resolver.realpath(__filename);
const EXCLUDE = SELF_REAL ? [SELF_REAL] : [];
const VALID_METHODS = ["auto", "native"];

/** The wrapper itself, including the npm bin shim that execs it. */
function isSelf(file) {
  return file === SELF_REAL || resolver.isNpmShim(file);
}

/**
 * A writable directory whose path is pure ASCII and space-free, for the
 * delegation .bat (a quoted /c argument would reintroduce the escaping
 * problems the .bat route exists to avoid).
 */
function batDir() {
  const candidates = [os.tmpdir(), path.dirname(__filename), os.homedir()].filter(Boolean);
  for (const dir of candidates) {
    if (/[^\x20-\x7e]/.test(dir)) continue;
    try {
      fs.accessSync(dir, fs.constants.W_OK);
      return dir;
    } catch {
      /* try the next candidate */
    }
  }
  return candidates[0] || ".";
}

function fail(message, code = 1) {
  process.stderr.write(`${message}\n`);
  process.exit(code);
}

function note(message) {
  process.stderr.write(`${message}\n`);
}

/** Spawn *bin* (bat-delegated on Windows when needed); returns the child. */
function spawnChild(bin, args) {
  const inv = resolver.childInvocation(bin, args, batDir(), process.env.comspec);
  const child = spawn(inv.bin, inv.args, { stdio: "inherit", env: process.env });
  if (inv.cleanup) {
    child.on("exit", () => resolver.cleanupBat(inv.cleanup));
  }
  return child;
}

/** Spawn a child that inherits stdio; forward exit code and signals. */
function run(bin, args) {
  const child = spawnChild(bin, args);
  const forward = (signal) => () => {
    try {
      child.kill(signal);
    } catch {
      /* already gone */
    }
  };
  process.on("SIGINT", forward("SIGINT"));
  process.on("SIGTERM", forward("SIGTERM"));
  child.on("error", (err) => {
    fail(`[apex] failed to start '${bin}': ${err.message}`);
  });
  child.on("exit", (code, signal) => {
    if (signal) process.kill(process.pid, signal);
    process.exit(code == null ? 1 : code);
  });
}

function pathEnv() {
  return process.env.PATH || process.env.Path || "";
}

function methodRequested() {
  const requested = String(process.env.APEX_INSTALL_METHOD || "auto")
    .trim()
    .toLowerCase();
  if (!VALID_METHODS.includes(requested)) {
    fail(
      `[apex] APEX_INSTALL_METHOD=${requested} is not supported.\n` +
        "       APEX now ships only through npm and the native backend; " +
        "pip, pipx and uv channels were removed.\n" +
        "       Remove APEX_INSTALL_METHOD, or set it to 'native'."
    );
  }
  return requested;
}

/**
 * Locate or install the native backend; returns its path, or null when the
 * caller disabled provisioning (`APEX_SKIP_INSTALL=1`, `APEX_NATIVE=0`).
 */
async function resolveNative() {
  const onPath = resolver.findBinary("apex-rs", pathEnv());
  if (onPath) return onPath;

  const managed = native.binaryPath(process.env, os.homedir());
  if (fs.existsSync(managed)) return managed;

  if (process.env.APEX_SKIP_INSTALL === "1" || process.env.APEX_NATIVE === "0") {
    return null;
  }

  try {
    return await native.installNative({
      version: process.env.APEX_VERSION || "",
      env: process.env,
      log: note,
    });
  } catch (err) {
    fail(
      `[apex] could not install the native backend: ${err.message}\n` +
        "       Set APEX_INSTALL_DIR to a writable directory, or install it " +
        "manually with install.sh --method native."
    );
  }
}

function missingBinaryHint() {
  const reason =
    process.env.APEX_SKIP_INSTALL === "1"
      ? "APEX_SKIP_INSTALL=1"
      : "APEX_NATIVE=0 disables the download";
  return (
    `[apex] no apex executable found on PATH (${reason}).\n` +
    "       Set APEX_BINARY=/path/to/apex, unset APEX_SKIP_INSTALL/APEX_NATIVE, " +
    "or install the native backend:\n" +
    "       bash install.sh --method native"
  );
}

async function main() {
  const args = process.argv.slice(2);

  // Validate legacy method values before doing any work.
  methodRequested();

  // 1) Explicit override.
  if (process.env.APEX_BINARY) {
    run(process.env.APEX_BINARY, args);
    return;
  }

  // 2) Already installed somewhere on PATH (and not this wrapper or its
  //    npm shim — the latter would re-spawn the wrapper forever).
  const existing = resolver.findBinary("apex", pathEnv(), EXCLUDE, isSelf);
  if (existing) {
    run(existing, args);
    return;
  }

  // 3) Native backend (the only remaining distribution channel).
  const binary = await resolveNative();
  if (!binary) {
    fail(missingBinaryHint());
  }

  const httpPort = String(process.env.APEX_HTTP_PORT || "8765");

  // No arguments: start the full TUI connected to the native backend.
  if (args.length === 0) {
    note("[apex] installing native backend (apex-rs)…");
    note("[apex] starting native backend on port " + httpPort + "…");
    const server = spawn(binary, ["serve", "--port", httpPort], {
      detached: true,
      stdio: ["ignore", "pipe", "pipe"],
      env: process.env,
    });
    server.stdout.on("data", () => {});
    server.stderr.on("data", () => {});
    server.unref();

    // Wait for the native backend to answer on /health.
    const healthUrl = `http://127.0.0.1:${httpPort}/health`;
    let ready = false;
    for (let i = 0; i < 50; i++) {
      try {
        await fetchJson(healthUrl);
        ready = true;
        break;
      } catch {
        /* not ready yet */
      }
      await sleep(200);
    }
    if (!ready) {
      note(
        `[apex] native backend did not become reachable at ${healthUrl}; ` +
          "continuing anyway."
      );
    }

    note("[apex] preparing TUI frontend…");
    const tuiDirectory = await tui.ensureTuiFrontend();
    note("[apex] launching TUI (Ctrl+C to exit)…");
    tui.runTui(tuiDirectory, args);
    return;
  }

  // With arguments: run the native backend headless (serve, run, tools, …).
  note("[apex] using the native backend (apex-rs, headless).");
  run(binary, args);
}

/** Tiny GET helper returning the parsed JSON body, or throwing. */
async function fetchJson(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, { headers: { "User-Agent": "apex-npm-installer" } }, (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          try {
            resolve(JSON.parse(data));
          } catch {
            reject(new Error(`non-JSON health response: ${data}`));
          }
        });
        res.on("error", reject);
      })
      .on("error", reject);
  });
}

/** Sleep for ms milliseconds. */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

main().catch((err) => {
  fail(`[apex] ${err && err.message ? err.message : String(err)}`);
});
