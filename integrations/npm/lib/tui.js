"use strict";

/**
 * TUI frontend provisioning for the npm wrapper.
 *
 * The TUI (Ink + React) is downloaded as a source archive, its dependencies
 * are installed with bun or npm, and it is launched connected to the native
 * backend (apex-rs). Everything that touches the network or spawns a process
 * is injected so the unit tests stay hermetic.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const https = require("https");
const { spawnSync } = require("child_process");

const DEFAULT_TUI_URL =
  "https://github.com/Ggboykxz/APEX/archive/refs/heads/dev.zip";

/** Managed TUI install directory: `APEX_TUI_DIR` wins, then `~/.apex/tui-frontend`. */
function tuiDir(env = process.env, home = os.homedir()) {
  const override = env && env.APEX_TUI_DIR;
  if (override) return path.resolve(override);
  return path.join(home, ".apex", "tui-frontend");
}

/** SHA256 hex digest of a buffer. */
function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

/** Default downloader: GETs a URL over HTTPS, follows up to five redirects. */
function fetchFile(url, redirectsLeft = 5) {
  return new Promise((resolve, reject) => {
    const request = https.get(
      url,
      { headers: { "User-Agent": "apex-npm-installer" } },
      (response) => {
        const status = response.statusCode || 0;
        if (status >= 300 && status < 400 && response.headers.location) {
          response.resume();
          if (redirectsLeft <= 0) {
            reject(new Error(`too many redirects for ${url}`));
            return;
          }
          resolve(
            fetchFile(
              new URL(response.headers.location, url).toString(),
              redirectsLeft - 1
            )
          );
          return;
        }
        if (status !== 200) {
          response.resume();
          reject(new Error(`download failed: HTTP ${status} for ${url}`));
          return;
        }
        const chunks = [];
        response.on("data", (chunk) => chunks.push(chunk));
        response.on("end", () => resolve(Buffer.concat(chunks)));
        response.on("error", reject);
      }
    );
    request.on("error", reject);
    request.setTimeout(120000, () =>
      request.destroy(new Error(`timeout downloading ${url}`))
    );
  });
}

/** Reject archive members that would escape the destination directory. */
function assertSafeMembers(members, destination) {
  const root = path.resolve(destination);
  for (const member of members) {
    const target = path.resolve(root, member);
    if (target !== root && !target.startsWith(root + path.sep)) {
      throw new Error(`unsafe archive member: ${member}`);
    }
  }
}

/** List archive members with the system `tar`. */
function listArchive(archive) {
  const result = spawnSync("tar", ["-tf", archive], { encoding: "utf8" });
  if (result.error)
    throw new Error(`cannot run tar: ${result.error.message}`);
  if (result.status !== 0) {
    throw new Error(
      `cannot read archive ${path.basename(archive)}: ${
        result.stderr || ""
      }`.trim()
    );
  }
  return String(result.stdout || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

/** Extract a `.tar.gz`/`.zip` archive into `destination` after validating member paths. */
function extractArchive(archive, destination) {
  fs.mkdirSync(destination, { recursive: true });
  const members = listArchive(archive);
  assertSafeMembers(members, destination);

  const extracted = spawnSync("tar", ["-xf", archive, "-C", destination], {
    encoding: "utf8",
  });
  if (!extracted.error && extracted.status === 0) return;

  if (/\.zip$/i.test(archive) && process.platform === "win32") {
    const command = [
      "-NoProfile",
      "-NonInteractive",
      "-Command",
      `Expand-Archive -LiteralPath ${JSON.stringify(
        archive
      )} -DestinationPath ${JSON.stringify(destination)} -Force`,
    ];
    const fallback = spawnSync("powershell", command, { encoding: "utf8" });
    if (!fallback.error && fallback.status === 0) return;
    throw new Error(
      `cannot extract ${path.basename(archive)}: ${
        fallback.stderr || ""
      }`.trim()
    );
  }
  throw new Error(
    `cannot extract ${path.basename(archive)}: ${
      extracted.stderr || ""
    }`.trim()
  );
}

/** Recursively copy a directory. */
function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(s, d);
    } else {
      fs.copyFileSync(s, d);
    }
  }
}

/** Find the tui-frontend directory inside an extracted archive. */
function findTuiDirInArchive(root) {
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const full = path.join(root, entry.name);
    if (entry.name === "tui-frontend") return full;
    // Archive extracted from GitHub: APEX-dev/tui-frontend/
    const nested = findTuiDirInArchive(full);
    if (nested) return nested;
  }
  return null;
}

/** Find bun or npm on PATH. */
function findRuntime() {
  for (const name of ["bun", "npm"]) {
    for (const dir of String(process.env.PATH || "").split(
      process.platform === "win32" ? ";" : ":"
    )) {
      const candidate = path.join(dir, name);
      try {
        if (fs.existsSync(candidate) && fs.statSync(candidate).isFile())
          return candidate;
      } catch {
        /* ignore */
      }
    }
  }
  return null;
}

/**
 * Download, extract and install the TUI frontend; return its directory.
 * @param {object} [options]
 * @param {Function} [options.download] injectable downloader (default: fetchFile)
 * @param {Function} [options.extract] injectable extractor (default: extractArchive)
 * @param {Function} [options.runtime] injectable runtime resolver (default: findRuntime)
 * @param {NodeJS.ProcessEnv} [options.env]
 * @param {string} [options.home]
 * @param {(msg: string) => void} [options.log]
 * @returns {Promise<string>} absolute path of the TUI directory
 */
async function ensureTuiFrontend(options = {}) {
  const env = options.env || process.env;
  const home = options.home || os.homedir();
  const log = options.log || (() => {});
  const download = options.download || fetchFile;
  const extract = options.extract || extractArchive;
  const runtime = options.runtime || findRuntime;

  const dir = tuiDir(env, home);
  if (
    fs.existsSync(path.join(dir, "package.json")) &&
    fs.existsSync(path.join(dir, "node_modules", "ink"))
  ) {
    log("[apex] TUI frontend already installed.");
    return dir;
  }

  const url = env.APEX_TUI_URL || DEFAULT_TUI_URL;
  log(`[apex] downloading TUI frontend from ${url}…`);
  const payload = await download(url);

  const staging = fs.mkdtempSync(path.join(os.tmpdir(), "apex-tui-"));
  try {
    const archive = path.join(staging, "tui.zip");
    fs.writeFileSync(archive, payload);
    const unpacked = path.join(staging, "unpack");
    extract(archive, unpacked);

    const tuiSrc = findTuiDirInArchive(unpacked);
    if (!tuiSrc) throw new Error("archive does not contain tui-frontend/");

    fs.mkdirSync(dir, { recursive: true });
    copyDir(tuiSrc, dir);

    // Install TUI dependencies.
    log("[apex] installing TUI dependencies (first run)…");
    const runtimeBin = runtime();
    if (!runtimeBin) {
      throw new Error(
        "neither bun nor npm is available on PATH to install TUI dependencies"
      );
    }
    const installCmd = ["install"];
    const result = spawnSync(runtimeBin, installCmd, {
      cwd: dir,
      stdio: "inherit",
      timeout: 180000,
    });
    if (result.status !== 0) {
      throw new Error(`TUI dependency install failed (exit ${result.status})`);
    }

    log(`[apex] TUI frontend ready at ${dir}`);
    return dir;
  } finally {
    fs.rmSync(staging, { recursive: true, force: true });
  }
}

/** Launch the TUI frontend, connected to the native backend. */
function runTui(tuiDirPath, args = []) {
  const runtime = findRuntime();
  if (!runtime) {
    throw new Error(
      "neither bun nor npm is available on PATH to run the TUI"
    );
  }

  const entry = path.join(tuiDirPath, "src", "App.tsx");
  const cmd = runtime === "bun" ? ["run", "src/App.tsx"] : [entry];
  const child = require("child_process").spawn(runtime, cmd, {
    cwd: tuiDirPath,
    stdio: "inherit",
    env: { ...process.env, APEX: "1" },
  });

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
    console.error(`[apex] failed to start TUI: ${err.message}`);
    process.exit(1);
  });
  child.on("exit", (code, signal) => {
    if (signal) process.kill(process.pid, signal);
    process.exit(code == null ? 1 : code);
  });
}

module.exports = {
  DEFAULT_TUI_URL,
  tuiDir,
  sha256,
  fetchFile,
  assertSafeMembers,
  listArchive,
  extractArchive,
  copyDir,
  findTuiDirInArchive,
  findRuntime,
  ensureTuiFrontend,
  runTui,
};
