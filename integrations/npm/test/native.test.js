"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const { spawnSync } = require("child_process");

const native = require("../lib/native");

function tmpDir(prefix = "apex-native-test-") {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

/**
 * Build a real tar.gz containing `apex-rs` at the archive root. The system
 * tar used here is the same one the installer extracts with, so the test
 * exercises the extraction path rather than a mock.
 */
function makeTarball(dir, body = "#!/bin/sh\necho apex-rs\n") {
  const source = path.join(dir, "source");
  fs.mkdirSync(source);
  const binary = path.join(source, "apex-rs");
  fs.writeFileSync(binary, body);
  if (process.platform !== "win32") fs.chmodSync(binary, 0o755);
  const archive = path.join(dir, "apex-rs.tar.gz");
  const result = spawnSync("tar", ["-czf", archive, "-C", source, "apex-rs"], {
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  return fs.readFileSync(archive);
}

/** Build a real zip containing `apex-rs.exe` (Windows only). */
function makeZip(dir, body = "MZ fake binary") {
  const source = path.join(dir, "zipsource");
  fs.mkdirSync(source);
  fs.writeFileSync(path.join(source, "apex-rs.exe"), body);
  const archive = path.join(dir, "apex-rs.zip");
  const result = spawnSync(
    "powershell",
    [
      "-NoProfile",
      "-NonInteractive",
      "-Command",
      `Compress-Archive -Path ${JSON.stringify(path.join(source, "apex-rs.exe"))} -DestinationPath ${JSON.stringify(archive)} -Force`,
    ],
    { encoding: "utf8" }
  );
  assert.equal(result.status, 0, result.stderr);
  return fs.readFileSync(archive);
}

class FakeRelease {
  constructor(payload, { digest = null, urls = null } = {}) {
    this.payload = payload;
    this.digest = digest || crypto.createHash("sha256").update(payload).digest("hex");
    this.urls = urls || [];
  }

  fetch() {
    return async (url) => {
      this.urls.push(url);
      if (url.endsWith(".sha256")) return Buffer.from(`${this.digest}  asset\n`);
      return this.payload;
    };
  }
}

test("targetTriple maps every supported host", () => {
  assert.equal(native.targetTriple("linux", "x64"), "x86_64-unknown-linux-gnu");
  assert.equal(native.targetTriple("linux", "arm64"), "aarch64-unknown-linux-gnu");
  assert.equal(native.targetTriple("darwin", "x64"), "x86_64-apple-darwin");
  assert.equal(native.targetTriple("darwin", "arm64"), "aarch64-apple-darwin");
  assert.equal(native.targetTriple("win32", "x64"), "x86_64-pc-windows-msvc");
  assert.equal(native.targetTriple("win32", "arm64"), "aarch64-pc-windows-msvc");
});

test("targetTriple rejects unsupported hosts", () => {
  assert.equal(native.targetTriple("freebsd", "x64"), null);
  assert.equal(native.targetTriple("linux", "ia32"), null);
  assert.equal(native.targetTriple("linux", "mips"), null);
});

test("assetName picks the archive format per target", () => {
  assert.equal(native.assetName("x86_64-unknown-linux-gnu"), "apex-rs-x86_64-unknown-linux-gnu.tar.gz");
  assert.equal(native.assetName("aarch64-apple-darwin"), "apex-rs-aarch64-apple-darwin.tar.gz");
  assert.equal(native.assetName("x86_64-pc-windows-msvc"), "apex-rs-x86_64-pc-windows-msvc.zip");
});

test("binaryName is apex-rs (never apex) and adds .exe on Windows", () => {
  assert.equal(native.binaryName("linux"), "apex-rs");
  assert.equal(native.binaryName("darwin"), "apex-rs");
  assert.equal(native.binaryName("win32"), "apex-rs.exe");
});

test("releaseBase resolves latest and pinned versions", () => {
  const latest = "https://github.com/Ggboykxz/APEX/releases/latest/download";
  assert.equal(native.releaseBase(), latest);
  assert.equal(native.releaseBase("latest"), latest);
  assert.equal(native.releaseBase("2.5.0"), "https://github.com/Ggboykxz/APEX/releases/download/v2.5.0");
  assert.equal(native.releaseBase("v2.5.0"), "https://github.com/Ggboykxz/APEX/releases/download/v2.5.0");
});

test("installDir honours APEX_INSTALL_DIR then ~/.apex/bin", () => {
  const home = path.join(tmpDir(), "home");
  assert.equal(native.installDir({}, home), path.join(home, ".apex", "bin"));
  assert.equal(
    native.installDir({ APEX_INSTALL_DIR: path.join(home, "custom") }, home),
    path.join(home, "custom")
  );
  assert.equal(
    native.binaryPath({}, home, "win32"),
    path.join(home, ".apex", "bin", "apex-rs.exe")
  );
});

test("parseSha256 reads the digest out of a sidecar", () => {
  const digest = "a".repeat(64);
  assert.equal(native.parseSha256(`${digest}  apex-rs.tar.gz\n`), digest);
  assert.equal(native.parseSha256(`SHA256 (apex-rs) = ${digest.toUpperCase()}`), digest);
  assert.equal(native.parseSha256("not a digest"), null);
  assert.equal(native.parseSha256(null), null);
});

test("assertSafeMembers rejects paths that escape the destination", () => {
  const root = tmpDir();
  assert.doesNotThrow(() => native.assertSafeMembers(["apex-rs", "sub/apex-rs"], root));
  assert.throws(() => native.assertSafeMembers(["../evil"], root), /unsafe archive member/);
  assert.throws(() => native.assertSafeMembers(["/etc/passwd"], root), /unsafe archive member/);
});

test("installNative verifies and installs a tarball", async () => {
  const dir = tmpDir();
  const payload = makeTarball(dir);
  const release = new FakeRelease(payload);

  const destination = await native.installNative({
    version: "2.5.0",
    fetch: release.fetch(),
    env: { APEX_INSTALL_DIR: path.join(dir, "bin") },
    home: dir,
    platform: "linux",
    arch: "x64",
  });

  assert.equal(destination, path.join(dir, "bin", "apex-rs"));
  assert.equal(fs.readFileSync(destination, "utf8"), "#!/bin/sh\necho apex-rs\n");
  assert.deepEqual(release.urls, [
    "https://github.com/Ggboykxz/APEX/releases/download/v2.5.0/apex-rs-x86_64-unknown-linux-gnu.tar.gz.sha256",
    "https://github.com/Ggboykxz/APEX/releases/download/v2.5.0/apex-rs-x86_64-unknown-linux-gnu.tar.gz",
  ]);
});

test("installNative defaults to the latest release", async () => {
  const dir = tmpDir();
  const release = new FakeRelease(makeTarball(dir));
  await native.installNative({
    fetch: release.fetch(),
    env: { APEX_INSTALL_DIR: path.join(dir, "bin") },
    home: dir,
    platform: "darwin",
    arch: "arm64",
  });
  assert.match(release.urls[0], /releases\/latest\/download\/apex-rs-aarch64-apple-darwin\.tar\.gz\.sha256$/);
});

test("installNative refuses a checksum mismatch without writing the binary", async () => {
  const dir = tmpDir();
  const release = new FakeRelease(makeTarball(dir));
  release.digest = "0".repeat(64);

  await assert.rejects(
    native.installNative({
      version: "2.5.0",
      fetch: release.fetch(),
      env: { APEX_INSTALL_DIR: path.join(dir, "bin") },
      home: dir,
      platform: "linux",
      arch: "x64",
    }),
    /checksum mismatch/
  );
  assert.equal(fs.existsSync(path.join(dir, "bin", "apex-rs")), false);
});

test("installNative refuses an unsupported host", async () => {
  await assert.rejects(
    native.installNative({
      fetch: async () => Buffer.alloc(0),
      env: {},
      home: tmpDir(),
      platform: "freebsd",
      arch: "x64",
    }),
    /no native backend build/
  );
});

test("installNative rejects an archive without the expected binary", async () => {
  const dir = tmpDir();
  const source = path.join(dir, "source");
  fs.mkdirSync(source);
  fs.writeFileSync(path.join(source, "other"), "x");
  const archive = path.join(dir, "apex-rs.tar.gz");
  assert.equal(spawnSync("tar", ["-czf", archive, "-C", source, "other"]).status, 0);
  const release = new FakeRelease(fs.readFileSync(archive));

  await assert.rejects(
    native.installNative({
      fetch: release.fetch(),
      env: { APEX_INSTALL_DIR: path.join(dir, "bin") },
      home: dir,
      platform: "linux",
      arch: "x64",
    }),
    /does not contain apex-rs/
  );
  assert.equal(fs.existsSync(path.join(dir, "bin", "apex-rs")), false);
});

test(
  "installNative extracts a Windows zip over PowerShell",
  { skip: process.platform !== "win32" },
  async () => {
    const dir = tmpDir();
    const release = new FakeRelease(makeZip(dir));
    const destination = await native.installNative({
      fetch: release.fetch(),
      env: { APEX_INSTALL_DIR: path.join(dir, "bin") },
      home: dir,
      platform: "win32",
      arch: "x64",
    });
    assert.equal(destination, path.join(dir, "bin", "apex-rs.exe"));
    assert.equal(fs.readFileSync(destination, "utf8"), "MZ fake binary");
  }
);
