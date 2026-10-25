#!/usr/bin/env node
"use strict";

/**
 * apex — npm wrapper for the APEX CLI.
 *
 * Resolution order:
 *   1. APEX_BINARY env var (explicit override, always wins)
 *   2. a real `apex` executable already on PATH (pip/pipx/uv install)
 *   3. first run: provision the Python package via pipx > uv > pip,
 *      then run it through the installer's own runner so no PATH change is
 *      required.
 *
 * Environment:
 *   APEX_BINARY        path to a pre-existing apex executable (override)
 *   APEX_VERSION       pin the Python package version (e.g. 2.5.0)
 *   APEX_INSTALL_METHOD pipx | uv | pip | auto (default: auto)
 *   APEX_SKIP_INSTALL  set to 1 to fail fast when apex is not found
 */

const { spawn, spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const resolver = require("../lib/resolver");

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

function main() {
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

  if (process.env.APEX_SKIP_INSTALL === "1") {
    fail(
      "[apex] no apex executable found on PATH and APEX_SKIP_INSTALL=1.\n" +
        "       Install manually (pipx install apex-ai / uv tool install apex-ai / " +
        "python3 -m pip install apex-ai) or set APEX_BINARY."
    );
  }

  // 3) First run: provision the Python package.
  const python = resolver.findPython(pathEnv());
  const flags = {
    pipx: resolver.commandExists("pipx", pathEnv()),
    uv: resolver.commandExists("uv", pathEnv()),
    python: Boolean(python),
  };
  const requested = process.env.APEX_INSTALL_METHOD || "auto";
  if (requested !== "auto" && !flags[requested]) {
    fail(
      `[apex] APEX_INSTALL_METHOD=${requested} but '${requested}' is not available ` +
        `(pipx=${flags.pipx} uv=${flags.uv} python=${flags.python}).`
    );
  }
  const installer =
    requested === "auto" ? resolver.chooseInstaller(flags) : requested;
  if (!installer) {
    fail(
      "[apex] could not provision APEX: no pipx, uv or python interpreter found.\n" +
        "       Install Python 3.11+ first, then either pipx (python3 -m pip install --user pipx) " +
        "or uv (curl -LsSf https://astral.sh/uv/install.sh | sh), and re-run."
    );
  }

  process.stderr.write(
    `[apex] first run — installing the apex-ai Python package via ${installer}…\n`
  );
  if (!install(installer)) {
    fail(
      `[apex] automatic installation via ${installer} failed. ` +
        `Manual install: ${resolver.manualHint(installer, process.env.APEX_VERSION || "")}`
    );
  }

  const runSpec = resolver.runCommand(installer, python);
  run(resolver.resolveRunner(runSpec.bin, pathEnv()), [...runSpec.args, ...args]);
}

main();
