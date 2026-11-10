"use strict";

/**
 * Native backend (`apex-rs`) provisioning for the npm wrapper.
 *
 * The native backend is the only binary the wrapper runs: APEX is distributed
 * through npm and the verified GitHub Release assets, and the Python package
 * is no longer published. This module knows how to map the host to a Rust
 * target triple, download the matching release asset with its `.sha256`
 * sidecar, verify the digest and extract the binary into a managed directory
 * (`~/.apex/bin` by default).
 *
 * Everything that touches the network or spawns a process is injected so the
 * unit tests stay hermetic (no network, no real download).
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const https = require("https");
const { spawnSync } = require("child_process");

const REPO = "Ggboykxz/APEX";
const ARCHIVE_ROOT = "apex-rs";

const ARCH_BY_NODE = { x64: "x86_64", arm64: "aarch64" };

/**
 * Map a Node platform/arch pair to a Rust release target triple.
 * @param {string} [platform] process.platform value
 * @param {string} [arch] process.arch value
 * @returns {string|null}
 */
function targetTriple(platform = process.platform, arch = process.arch) {
  const cpu = ARCH_BY_NODE[String(arch).toLowerCase()];
  if (!cpu) return null;
  switch (platform) {
    case "linux":
      return `${cpu}-unknown-linux-gnu`;
    case "darwin":
      return `${cpu}-apple-darwin`;
    case "win32":
      return `${cpu}-pc-windows-msvc`;
    default:
      return null;
  }
}

/** Return the release asset file name for a target triple. */
function assetName(triple) {
  const extension = triple.includes("windows") ? "zip" : "tar.gz";
  return `${ARCHIVE_ROOT}-${triple}.${extension}`;
}

/** Return the managed native executable name for a platform. */
function binaryName(platform = process.platform) {
  return platform === "win32" ? `${ARCHIVE_ROOT}.exe` : ARCHIVE_ROOT;
}

/**
 * Base URL of a GitHub release download directory (latest or pinned).
 * @param {string} [version] exact version, with or without a leading `v`
 */
function releaseBase(version = "") {
  const pinned = String(version || "")
    .trim()
    .replace(/^v/i, "");
  if (pinned && pinned !== "latest") {
    return `https://github.com/${REPO}/releases/download/v${pinned}`;
  }
  return `https://github.com/${REPO}/releases/latest/download`;
}

/**
 * Managed install directory: `APEX_INSTALL_DIR` wins, then `~/.apex/bin`.
 * @param {NodeJS.ProcessEnv|Record<string,string>} [env]
 * @param {string} [home]
 */
function installDir(env = process.env, home = os.homedir()) {
  const override = env && env.APEX_INSTALL_DIR;
  if (override) return path.resolve(override);
  return path.join(home, ".apex", "bin");
}

/** Managed native executable path. */
function binaryPath(env = process.env, home = os.homedir(), platform = process.platform) {
  return path.join(installDir(env, home), binaryName(platform));
}

/** SHA256 hex digest of a buffer. */
function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

/** Extract a SHA256 digest from a `.sha256` sidecar body, or null. */
function parseSha256(text) {
  const match = /\b([0-9a-fA-F]{64})\b/.exec(String(text || ""));
  return match ? match[1].toLowerCase() : null;
}

/**
 * Default downloader: GETs a URL over HTTPS, follows up to five redirects and
 * resolves with the response body as a Buffer.
 * @param {string} url
 * @param {number} [redirectsLeft]
 * @returns {Promise<Buffer>}
 */
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
          resolve(fetchFile(new URL(response.headers.location, url).toString(), redirectsLeft - 1));
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
    request.setTimeout(120000, () => request.destroy(new Error(`timeout downloading ${url}`)));
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

/**
 * List archive members with the system `tar` (bsdtar on Windows/macOS reads
 * both tar and zip; GNU tar reads tar only).
 * @returns {string[]}
 */
function listArchive(archive) {
  const result = spawnSync("tar", ["-tf", archive], { encoding: "utf8" });
  if (result.error) throw new Error(`cannot run tar: ${result.error.message}`);
  if (result.status !== 0) {
    throw new Error(`cannot read archive ${path.basename(archive)}: ${result.stderr || ""}`.trim());
  }
  return String(result.stdout || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

/**
 * Extract a `.tar.gz`/`.zip` archive into `destination` after validating
 * every member path. Uses the platform `tar` first, then PowerShell
 * `Expand-Archive` for zip files when `tar` cannot read them.
 * @param {string} archive
 * @param {string} destination
 */
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
      `Expand-Archive -LiteralPath ${JSON.stringify(archive)} -DestinationPath ${JSON.stringify(destination)} -Force`,
    ];
    const fallback = spawnSync("powershell", command, { encoding: "utf8" });
    if (!fallback.error && fallback.status === 0) return;
    throw new Error(`cannot extract ${path.basename(archive)}: ${fallback.stderr || ""}`.trim());
  }
  throw new Error(`cannot extract ${path.basename(archive)}: ${extracted.stderr || ""}`.trim());
}

/** Recursively find a file named `name` under `root`. */
function findFile(root, name) {
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) {
      const nested = findFile(full, name);
      if (nested) return nested;
    } else if (entry.isFile() && entry.name === name) {
      return full;
    }
  }
  return null;
}

/**
 * Download, verify and install the native backend.
 *
 * @param {object} [options]
 * @param {string} [options.version] pinned version (default: latest)
 * @param {NodeJS.ProcessEnv} [options.env]
 * @param {string} [options.home]
 * @param {string} [options.platform]
 * @param {string} [options.arch]
 * @param {(url: string) => Promise<Buffer>|Buffer} [options.fetch]
 * @param {(msg: string) => void} [options.log]
 * @returns {Promise<string>} absolute path of the installed binary
 */
async function installNative(options = {}) {
  const platform = options.platform || process.platform;
  const arch = options.arch || process.arch;
  const env = options.env || process.env;
  const home = options.home || os.homedir();
  const log = options.log || (() => {});
  const download = options.fetch || fetchFile;

  const triple = targetTriple(platform, arch);
  if (!triple) {
    throw new Error(`no native backend build for ${platform}/${arch}`);
  }

  const base = releaseBase(options.version);
  const asset = assetName(triple);
  log(`[apex] downloading ${asset}…`);

  const checksumText = await download(`${base}/${asset}.sha256`);
  const checksum = parseSha256(Buffer.isBuffer(checksumText) ? checksumText.toString("utf8") : checksumText);
  if (!checksum) throw new Error("release checksum file is missing a SHA256 digest");

  const payload = await download(`${base}/${asset}`);
  const body = Buffer.isBuffer(payload) ? payload : Buffer.from(payload);
  if (sha256(body) !== checksum) {
    throw new Error("native backend checksum mismatch");
  }

  const staging = fs.mkdtempSync(path.join(os.tmpdir(), "apex-native-"));
  try {
    const archive = path.join(staging, asset);
    fs.writeFileSync(archive, body);
    const unpacked = path.join(staging, "unpack");
    extractArchive(archive, unpacked);

    const name = binaryName(platform);
    const found = findFile(unpacked, name);
    if (!found) throw new Error(`archive does not contain ${name}`);

    const directory = installDir(env, home);
    fs.mkdirSync(directory, { recursive: true });
    const destination = path.join(directory, name);
    fs.copyFileSync(found, destination);
    if (platform !== "win32") fs.chmodSync(destination, 0o755);
    log(`[apex] installed ${name} at ${destination}`);
    return destination;
  } finally {
    fs.rmSync(staging, { recursive: true, force: true });
  }
}

module.exports = {
  REPO,
  targetTriple,
  assetName,
  binaryName,
  releaseBase,
  installDir,
  binaryPath,
  sha256,
  parseSha256,
  fetchFile,
  assertSafeMembers,
  listArchive,
  extractArchive,
  findFile,
  installNative,
};
