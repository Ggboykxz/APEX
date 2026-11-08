"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");

const resolver = require("../lib/resolver");

const IS_WINDOWS = process.platform === "win32";
const PATH_SEP = IS_WINDOWS ? ";" : ":";

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "apex-npm-test-"));
}

function makeBin(dir, name) {
  const file = path.join(dir, name);
  fs.writeFileSync(file, IS_WINDOWS ? "@echo off\n" : "#!/bin/sh\necho fake\n");
  if (!IS_WINDOWS) fs.chmodSync(file, 0o755);
  return file;
}

// The real APEX console entry point is "apex"; npm adds a .cmd shim on Windows.
const APEX_NAME = IS_WINDOWS ? "apex.cmd" : "apex";

test("splitPath splits on the platform separator and drops empty entries", () => {
  const env = `/a${PATH_SEP}  /b ${PATH_SEP}${PATH_SEP}/c`;
  assert.deepEqual(resolver.splitPath(env), ["/a", "/b", "/c"]);
  assert.deepEqual(resolver.splitPath(""), []);
  assert.deepEqual(resolver.splitPath(undefined), []);
});

test("findBinary locates an executable on PATH", () => {
  const dir = tmpDir();
  const file = makeBin(dir, APEX_NAME);
  assert.equal(resolver.findBinary("apex", dir), file);
  assert.equal(resolver.findBinary("apex", `${dir}${PATH_SEP}/nonexistent`), file);
});

test("findBinary returns null when the binary is absent", () => {
  const dir = tmpDir();
  makeBin(dir, "other");
  assert.equal(resolver.findBinary("apex", dir), null);
  assert.equal(resolver.findBinary("apex", ""), null);
});

if (!IS_WINDOWS) {
  test("findBinary skips files without the executable bit", () => {
    const dir = tmpDir();
    const file = path.join(dir, "apex");
    fs.writeFileSync(file, "#!/bin/sh\n");
    fs.chmodSync(file, 0o644);
    assert.equal(resolver.findBinary("apex", dir), null);
  });
}

test("findBinary excludes its own realpath (wrapper self-detection)", () => {
  const dir = tmpDir();
  const file = makeBin(dir, APEX_NAME);
  const real = resolver.realpath(file);
  assert.equal(resolver.findBinary("apex", dir, [real]), null);
});

test("findBinary finds the native backend by its apex-rs name", () => {
  const dir = tmpDir();
  makeBin(dir, IS_WINDOWS ? "apex-rs.exe" : "apex-rs");
  assert.notEqual(resolver.findBinary("apex-rs", dir), null);
  assert.equal(resolver.findBinary("apex", dir), null);
});

test("realpath falls back to the input for missing files", () => {
  const missing = path.join(tmpDir(), "does-not-exist");
  assert.equal(resolver.realpath(missing), missing);
});

test("batchQuote quotes every argument and drops quote/percent", () => {
  assert.equal(resolver.batchQuote("--version"), '"--version"');
  assert.equal(resolver.batchQuote("fix the bug"), '"fix the bug"');
  assert.equal(resolver.batchQuote(""), '""');
  // % would trigger %VAR% expansion when the bat line is parsed; " would
  // break tokenization. Both are dropped; everything else is inert inside
  // the quotes.
  assert.equal(resolver.batchQuote("%PATH% & del"), '"PATH & del"');
  assert.equal(resolver.batchQuote('say "hi"'), '"say hi"');
});

test("writeDelegationBat writes a chcp-65001 bat with one quoted line", () => {
  const dir = tmpDir();
  const batPath = resolver.writeDelegationBat("C:\\bin\\apex.cmd", ["--version", "fix the bug"], dir);
  assert.equal(path.dirname(batPath), dir);
  assert.match(
    path.basename(batPath),
    /^apex-delegate-\d+[-]\d+[-][0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.bat$/
  );
  const lines = fs.readFileSync(batPath, "utf8").split("\r\n");
  assert.equal(lines[0], "@echo off");
  assert.equal(lines[1], "chcp 65001 >nul 2>nul");
  assert.equal(lines[2], '"C:\\bin\\apex.cmd" "--version" "fix the bug"');
  assert.equal(lines[3], "exit /b %ERRORLEVEL%");
  // On POSIX the mode is meaningful: owner read/write only (0o600).
  if (!IS_WINDOWS) {
    assert.equal(fs.statSync(batPath).mode & 0o777, 0o600);
  }
  resolver.cleanupBat(batPath);
  assert.throws(() => fs.readFileSync(batPath, "utf8"));
});

test("childInvocation routes .cmd/.bat/.ps1 through a temp bat on Windows", () => {
  const dir = tmpDir();
  const comspec = IS_WINDOWS ? process.env.comspec : "C:\\custom\\cmd.exe";
  const inv = resolver.childInvocation("C:\\bin\\apex.cmd", ["a b"], dir, comspec);
  if (IS_WINDOWS) {
    assert.equal(inv.bin, process.env.comspec);
    assert.deepEqual(inv.args, ["/c", inv.cleanup]);
    assert.ok(fs.existsSync(inv.cleanup), "delegation bat must exist");
    resolver.cleanupBat(inv.cleanup);
  } else {
    // POSIX: no delegation, the target is spawned directly.
    assert.equal(inv.bin, "C:\\bin\\apex.cmd");
    assert.deepEqual(inv.args, ["a b"]);
    assert.equal(inv.cleanup, undefined);
  }
  const direct = resolver.childInvocation("apex.exe", ["x"], dir, comspec);
  assert.equal(direct.bin, "apex.exe");
  assert.deepEqual(direct.args, ["x"]);
});

test("isNpmShim detects the npm bin shim that execs the wrapper", () => {
  const dir = tmpDir();
  const winShim = path.join(dir, "apex.cmd");
  fs.writeFileSync(winShim, '@echo off\r\nnode "%dp0%\\node_modules\\apex-ai\\bin\\apex.js" %*\r\n');
  assert.equal(resolver.isNpmShim(winShim), true);

  const posixShim = path.join(dir, "apex.sh");
  fs.writeFileSync(posixShim, '#!/bin/sh\nexec node "/opt/npm/node_modules/apex-ai/bin/apex.js" "$@"\n');
  assert.equal(resolver.isNpmShim(posixShim), true);

  // A launcher that points at a real binary (not node_modules/apex-ai) is kept.
  const nativeShim = path.join(dir, "apex-real.cmd");
  fs.writeFileSync(nativeShim, '@echo off\r\n"%USERPROFILE%\\.apex\\bin\\apex-rs.exe" %*\r\n');
  assert.equal(resolver.isNpmShim(nativeShim), false);

  assert.equal(resolver.isNpmShim(path.join(dir, "missing")), false);
});

test("findBinary skips self npm shims via the isSelf predicate", () => {
  const dir = tmpDir();
  const shim = path.join(dir, APEX_NAME);
  fs.writeFileSync(shim, '@echo off\nnode "x/node_modules/apex-ai/bin/apex.js" %*\n');
  if (!IS_WINDOWS) fs.chmodSync(shim, 0o755);
  assert.equal(resolver.findBinary("apex", dir), shim);
  assert.equal(resolver.findBinary("apex", dir, [], (f) => f === shim), null);
});
