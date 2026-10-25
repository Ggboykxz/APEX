"use strict";

/**
 * Pure resolution logic for the apex npm wrapper.
 *
 * Everything that touches the filesystem or the environment is injected or
 * parameterised so the unit tests can run on any platform without a real
 * Python installation. The entry point (bin/apex.js) only orchestrates.
 */

const fs = require("fs");
const path = require("path");

const IS_WINDOWS = process.platform === "win32";
const PATH_SEP = IS_WINDOWS ? ";" : ":";
// npm creates .cmd shims on Windows; console scripts get .exe there too.
const BINARY_SUFFIXES = IS_WINDOWS ? [".cmd", ".exe", ".ps1", ""] : [""];

function splitPath(pathEnv) {
  return String(pathEnv || "")
    .split(PATH_SEP)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

/** Resolve symlinks when possible; never throws. */
function realpath(file) {
  try {
    return fs.realpathSync(file);
  } catch {
    return file;
  }
}

function isExecutable(file) {
  if (IS_WINDOWS) return true;
  try {
    fs.accessSync(file, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

/**
 * Locate an executable named `name` on PATH.
 *
 * @param {string} name binary name without suffix (e.g. "apex")
 * @param {string} pathEnv the PATH environment value
 * @param {string[]} [excludeRealpaths] realpaths that must be skipped
 *   (used to make the wrapper ignore itself when npm puts its own bin dir
 *   on PATH)
 * @param {((file: string) => boolean)|null} [isSelf] extra predicate for
 *   "this candidate is the wrapper itself" (e.g. the npm bin shim, whose
 *   realpath differs from the entry point but whose body invokes it)
 * @returns {string|null} absolute path of the binary, or null
 */
function findBinary(name, pathEnv, excludeRealpaths = [], isSelf = null) {
  const excluded = new Set(excludeRealpaths);
  for (const dir of splitPath(pathEnv)) {
    for (const suffix of BINARY_SUFFIXES) {
      const candidate = path.join(dir, `${name}${suffix}`);
      let real;
      try {
        if (!fs.existsSync(candidate)) continue;
        real = realpath(candidate);
      } catch {
        continue;
      }
      if (excluded.has(real) || (isSelf && isSelf(real))) continue;
      let stat;
      try {
        stat = fs.statSync(real);
      } catch {
        continue;
      }
      if (stat.isFile() && isExecutable(candidate)) return real;
    }
  }
  return null;
}

/** Find a usable Python 3 interpreter (python3 first, then python). */
function findPython(pathEnv) {
  return findBinary("python3", pathEnv) || findBinary("python", pathEnv);
}

function commandExists(cmd, pathEnv, excludeRealpaths = []) {
  return findBinary(cmd, pathEnv, excludeRealpaths) !== null;
}

/**
 * Pick the provisioning strategy, best-isolated-first.
 * @param {{pipx?: boolean, uv?: boolean, python?: boolean}} flags
 */
function chooseInstaller(flags) {
  if (flags.pipx) return "pipx";
  if (flags.uv) return "uv";
  if (flags.python) return "pip";
  return null;
}

/**
 * Command used to (re)install the Python package.
 * @param {"pipx"|"uv"|"pip"} installer
 * @param {string|null} pythonPath python interpreter (pip path only)
 * @param {string} [version] optional exact version pin (e.g. "2.5.0")
 */
function installCommand(installer, pythonPath, version = "") {
  const spec = version ? `apex-ai==${version}` : "apex-ai";
  switch (installer) {
    case "pipx":
      return { bin: "pipx", args: ["install", spec] };
    case "uv":
      return { bin: "uv", args: ["tool", "install", spec] };
    case "pip":
      return { bin: pythonPath || "python3", args: ["-m", "pip", "install", spec] };
    default:
      throw new Error(`unknown installer: ${installer}`);
  }
}

/**
 * Command that runs the installed CLI without requiring its bin dir on PATH.
 * @param {"pipx"|"uv"|"pip"} installer
 * @param {string|null} pythonPath python interpreter (pip path only)
 */
function runCommand(installer, pythonPath) {
  switch (installer) {
    case "pipx":
      return { bin: "pipx", args: ["run", "apex-ai", "--"] };
    case "uv":
      return { bin: "uv", args: ["tool", "run", "apex-ai", "--"] };
    case "pip":
      return { bin: pythonPath || "python3", args: ["-m", "apex"] };
    default:
      throw new Error(`unknown installer: ${installer}`);
  }
}

/** Human-readable manual install hint for a given installer. */
function manualHint(installer, version = "") {
  const spec = version ? `apex-ai==${version}` : "apex-ai";
  switch (installer) {
    case "pipx":
      return `pipx install ${spec}`;
    case "uv":
      return `uv tool install ${spec}`;
    default:
      return `python3 -m pip install ${spec}`;
  }
}

/**
 * Quote one argument for a batch (.cmd/.bat) command line.
 *
 * cmd.exe cannot represent a double quote or a %VAR% expansion *inside* a
 * quoted region, so both are dropped: `"` would break tokenization and `%`
 * would trigger environment expansion when the line is parsed. Everything
 * else — spaces, & | < > ^ ! ; ( ) — is inert inside double quotes in a
 * non-interactive cmd.
 */
function batchQuote(arg) {
  const value = String(arg);
  if (value === "") return '""';
  return `"${value.replace(/["%]/g, "")}"`;
}

let batSeq = 0;

/**
 * Write a temporary .bat file that delegates to a .cmd/.bat/.ps1 target.
 *
 * Node on Windows cannot pass a multi-word argument through to a .cmd:
 * libuv escapes argv with MSVC rules (`\"`) that cmd.exe does not understand,
 * `shell: true` concatenates arguments without escaping (DEP0190), and
 * PowerShell 5.1 injects literal quotes around space-bearing arguments when
 * it calls a batch file. A .bat file written by us has no intermediate
 * escaping layer at all — the bytes we write are exactly the command line
 * cmd executes — and `cmd /c <path>` carries no quotes to mangle.
 *
 * The file is written as UTF-8 with a `chcp 65001` preamble so that
 * non-ASCII arguments (accents, CJK) survive the cmd code page.
 *
 * @param {string} target absolute path of the .cmd/.bat to run
 * @param {string[]} args arguments to pass through
 * @param {string} batDir a writable directory whose path is pure ASCII
 *   (spaces would require quoting the /c argument and bring the escaping
 *   problems back)
 * @returns {string} absolute path of the written .bat file
 */
function writeDelegationBat(target, args, batDir) {
  batSeq += 1;
  const batPath = path.join(batDir, `apex-delegate-${process.pid}-${batSeq}.bat`);
  const line = [batchQuote(target), ...args.map(batchQuote)].join(" ");
  const content = `@echo off\r\nchcp 65001 >nul 2>nul\r\n${line}\r\nexit /b %ERRORLEVEL%\r\n`;
  fs.writeFileSync(batPath, content, "utf8");
  return batPath;
}

/**
 * Resolve a bare runner name (pipx, uv, python3) to the real file on PATH.
 *
 * Absolute paths are returned unchanged. Resolving lets .cmd variants take
 * the bat-delegation route in childInvocation and avoids PATH surprises in
 * the child. Falls back to the input when nothing is found (the error
 * message will still point at the missing command).
 *
 * @param {string} bin
 * @param {string} pathEnv
 * @returns {string}
 */
function resolveRunner(bin, pathEnv) {
  const name = String(bin);
  if (name.includes("\\") || name.includes("/")) return name;
  const bare = name.replace(/\.(cmd|bat|ps1|exe)$/i, "");
  return findBinary(bare, pathEnv) || name;
}

/**
 * Compute the actual spawn spec for `bin` with `args`.
 *
 * On Windows, .cmd/.bat/.ps1 targets cannot be spawned directly with intact
 * arguments (see writeDelegationBat): they are delegated through a temporary
 * .bat file run with `cmd /c`. The returned `cleanup` path (when present)
 * must be unlinked once the child exits.
 *
 * @param {string} bin
 * @param {string[]} args
 * @param {string} [batDir] directory for the delegation .bat (Windows only)
 * @param {string} [comspec] path to cmd.exe (Windows only; Node does not
 *   search the system directory for bare command names)
 * @returns {{bin: string, args: string[], cleanup?: string}}
 */
function childInvocation(bin, args, batDir, comspec) {
  if (IS_WINDOWS && /\.(cmd|bat|ps1)$/i.test(String(bin))) {
    const batPath = writeDelegationBat(bin, args, batDir);
    return {
      bin: comspec || process.env.comspec || "C:\\Windows\\System32\\cmd.exe",
      args: ["/c", batPath],
      cleanup: batPath,
    };
  }
  return { bin, args };
}

/** Best-effort removal of a delegation .bat after the child exits. */
function cleanupBat(batPath) {
  if (!batPath) return;
  try {
    fs.unlinkSync(batPath);
  } catch {
    /* already gone */
  }
}

/**
 * Detect the shim that `npm install -g` creates next to the wrapper itself.
 *
 * On Windows that shim is `apex.cmd` (on POSIX, a shell script `apex`); its
 * realpath differs from the wrapper's `bin/apex.js`, so the realpath-based
 * self-exclusion cannot catch it. Running the wrapper through that shim
 * would re-find the shim on PATH and spawn itself forever, so any candidate
 * whose body invokes our own entry point is treated as self.
 *
 * @param {string} file
 * @returns {boolean}
 */
function isNpmShim(file) {
  try {
    const st = fs.statSync(file);
    if (!st.isFile() || st.size > 16384) return false;
    const head = fs.readFileSync(file, "latin1");
    return head.replace(/\\/g, "/").includes("node_modules/apex-ai/bin/apex.js");
  } catch {
    return false;
  }
}

module.exports = {
  splitPath,
  realpath,
  findBinary,
  findPython,
  commandExists,
  chooseInstaller,
  installCommand,
  runCommand,
  manualHint,
  batchQuote,
  writeDelegationBat,
  resolveRunner,
  childInvocation,
  cleanupBat,
  isNpmShim,
};
