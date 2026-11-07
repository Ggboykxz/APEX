#!/usr/bin/env node
"use strict";

/**
 * apex — npm wrapper for the APEX CLI.
 *
 * Resolution order:
 *   1. APEX_BINARY env var (explicit override, always wins)
 *   2. a real `apex` executable already on PATH (pip/pipx/uv install)
 *   3. the native backend when requested: APEX_INSTALL_METHOD=native or
 *      APEX_PREFER_NATIVE=1 (downloads `apex-rs` if it is missing)
 *   4. first run: provision the Python package via pipx > uv > pip, then run
 *      it through the installer's own runner so no PATH change is required
 *   5. the native backend as a fallback when no Python toolchain exists and
 *      APEX_NATIVE is not 0
 *
 * The Python CLI/TUI stays the default: the native backend is headless
 * (`serve`, `run`, `tools`, …) and is opt-in.
 *
 * Environment:
 *   APEX_BINARY        path to a pre-existing apex executable (override)
 *   APEX_VERSION       pin the release version (e.g. 2.5.0)
 *   APEX_INSTALL_METHOD pipx | uv | pip | native | auto (default: auto)
 *   APEX_PREFER_NATIVE set to 1 to prefer the native backend
 *   APEX_NATIVE        set to 0 to disable the native fallback
 *   APEX_SKIP_INSTALL  set to 1 to fail fast when apex is not found
 *   APEX_INSTALL_DIR   native backend install directory (default ~/.apex/bin)
 */

const { spawn, spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const resolver = require("../lib/resolver");
const native = require("../lib/native");

const SELF_REAL = resolver.realpath(__filename);
const EXCLUDE = SELF_REAL ? [SELF_REAL] : [];

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

function truthy(value) {
  return ["1", "true", "yes", "on"].includes(String(value || "").trim().toLowerCase());
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

/** Blocking install step; returns true on success. */
function install(installer) {
  const spec = resolver.installCommand(installer, pythonHint(), process.env.APEX_VERSION || "");
  const inv = resolver.childInvocation(
    resolver.resolveRunner(spec.bin, pathEnv()),
    spec.args,
    batDir(),
    process.env.comspec
  );
  const result = spawnSync(inv.bin, inv.args, { stdio: "inherit", env: process.env });
  resolver.cleanupBat(inv.cleanup);
  return (result.status ?? 1) === 0;
}

function pythonHint() {
  return process.env.APEX_INSTALL_METHOD === "pip" ? resolver.findPython(pathEnv()) || "python3" : null;
}

function pathEnv() {
  return process.env.PATH || process.env.Path || "";
}

/**
 * Locate or install the native backend; returns its path, or null when it
 * cannot be provisioned.
 */
async function resolveNative({ optional }) {
  const onPath = resolver.findBinary("apex-rs", pathEnv());
  if (onPath) return onPath;

  const managed = native.binaryPath(process.env, os.homedir());
  if (fs.existsSync(managed)) return managed;

  if (optional && process.env.APEX_SKIP_INSTALL === "1") return null;

  try {
    return await native.installNative({
      version: process.env.APEX_VERSION || "",
      env: process.env,
      log: note,
    });
  } catch (err) {
    if (optional) {
      note(`[apex] native backend unavailable: ${err.message}`);
      return null;
    }
    fail(
      `[apex] could not install the native backend: ${err.message}\n` +
        "       Set APEX_INSTALL_DIR to a writable directory, or install the Python CLI " +
        "(pipx install apex-ai)."
    );
  }
}

/** Provision the Python package and run it; exits or returns a failure message. */
function provisionPython(args) {
  const python = resolver.findPython(pathEnv());
  const flags = {
    pipx: resolver.commandExists("pipx", pathEnv()),
    uv: resolver.commandExists("uv", pathEnv()),
    python: Boolean(python),
  };
  const requested = process.env.APEX_INSTALL_METHOD || "auto";
  if (requested !== "auto" && !Object.prototype.hasOwnProperty.call(flags, requested)) {
    fail(`[apex] APEX_INSTALL_METHOD=${requested} is not a Python installer (pipx, uv or pip).`);
  }
  if (requested !== "auto" && !flags[requested]) {
    fail(
      `[apex] APEX_INSTALL_METHOD=${requested} but '${requested}' is not available ` +
        `(pipx=${flags.pipx} uv=${flags.uv} python=${flags.python}).`
    );
  }
  const installer = requested === "auto" ? resolver.chooseInstaller(flags) : requested;
  if (!installer) return null;

  note(`[apex] first run — installing the apex-ai Python package via ${installer}…`);
  if (!install(installer)) {
    fail(
      `[apex] automatic installation via ${installer} failed. ` +
        `Manual install: ${resolver.manualHint(installer, process.env.APEX_VERSION || "")}`
    );
  }

  const runSpec = resolver.runCommand(installer, python);
  run(resolver.resolveRunner(runSpec.bin, pathEnv()), [...runSpec.args, ...args]);
  return installer;
}

async function main() {
  const args = process.argv.slice(2);

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

  const requested = process.env.APEX_INSTALL_METHOD || "auto";

  // 3) Native backend when explicitly requested.
  if (requested === "native" || truthy(process.env.APEX_PREFER_NATIVE)) {
    const binary = await resolveNative({ optional: false });
    if (binary) {
      note("[apex] using the native backend (apex-rs, headless).");
      run(binary, args);
      return;
    }
  }

  if (process.env.APEX_SKIP_INSTALL === "1") {
    fail(
      "[apex] no apex executable found on PATH and APEX_SKIP_INSTALL=1.\n" +
        "       Install manually (pipx install apex-ai / uv tool install apex-ai / " +
        "python3 -m pip install apex-ai) or set APEX_BINARY."
    );
  }

  // 4) Default: provision the Python CLI/TUI.
  const installer = provisionPython(args);
  if (installer) return;

  // 5) No Python toolchain: fall back to the native backend unless disabled.
  if (process.env.APEX_NATIVE !== "0") {
    note("[apex] no pipx, uv or Python found — falling back to the native backend.");
    const binary = await resolveNative({ optional: true });
    if (binary) {
      run(binary, args);
      return;
    }
  }

  fail(
    "[apex] could not provision APEX: no pipx, uv or python interpreter found.\n" +
      "       Install Python 3.11+ first, then either pipx (python3 -m pip install --user pipx) " +
      "or uv (curl -LsSf https://astral.sh/uv/install.sh | sh), and re-run.\n" +
      "       Or install the native backend: npm install -g apex-ai && APEX_INSTALL_METHOD=native apex."
  );
}

main().catch((err) => {
  fail(`[apex] ${err && err.message ? err.message : String(err)}`);
});
