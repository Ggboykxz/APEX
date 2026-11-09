"use strict";

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  DEFAULT_TUI_URL,
  tuiDir,
  findRuntime,
  ensureTuiFrontend,
  extractArchive,
} from "../lib/tui.js";

describe("tuiDir", () => {
  it("defaults to ~/.apex/tui-frontend", () => {
    const dir = tuiDir({}, os.homedir());
    assert.strictEqual(dir, path.join(os.homedir(), ".apex", "tui-frontend"));
  });

  it("honours APEX_TUI_DIR", () => {
    const dir = tuiDir({ APEX_TUI_DIR: "/custom/tui" }, os.homedir());
    assert.strictEqual(dir, path.resolve("/custom/tui"));
  });
});

describe("findRuntime", () => {
  it("returns null when neither bun nor npm is on PATH", () => {
    const origEnv = process.env.PATH;
    process.env.PATH = "";
    try {
      assert.strictEqual(findRuntime(), null);
    } finally {
      process.env.PATH = origEnv;
    }
  });

  it("prefers bun over npm", () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "apex-runtime-"));
    try {
      fs.writeFileSync(path.join(tmp, "bun"), "", { mode: 0o755 });
      fs.writeFileSync(path.join(tmp, "npm"), "", { mode: 0o755 });
      const origEnv = process.env.PATH;
      process.env.PATH = tmp + path.delimiter + tmp;
      try {
        assert.strictEqual(findRuntime(), path.join(tmp, "bun"));
      } finally {
        process.env.PATH = origEnv;
      }
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });
});

describe("ensureTuiFrontend", () => {
  it("returns existing dir when already installed", async () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "apex-tui-"));
    try {
      const tuiDirPath = path.join(tmp, "tui-frontend");
      fs.mkdirSync(path.join(tuiDirPath, "node_modules", "ink"), {
        recursive: true,
      });
      fs.writeFileSync(path.join(tuiDirPath, "package.json"), "{}");

      const dir = await ensureTuiFrontend({
        env: { APEX_TUI_DIR: tuiDirPath },
        home: tmp,
        log: () => {},
      });
      assert.strictEqual(dir, tuiDirPath);
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });

  it("downloads and extracts when not present", async () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "apex-tui-"));
    try {
      const installDir = path.join(tmp, "tui-frontend");

      // Build a fake archive containing tui-frontend/package.json
      const staging = fs.mkdtempSync(path.join(os.tmpdir(), "apex-stage-"));
      const archive = path.join(staging, "tui.tar.gz");
      const unpacked = path.join(staging, "unpack", "APEX-dev", "tui-frontend");
      fs.mkdirSync(path.join(unpacked, "node_modules", "ink"), {
        recursive: true,
      });
      fs.writeFileSync(path.join(unpacked, "package.json"), "{}");

      const { spawnSync } = await import("node:child_process");
      const tar = spawnSync(
        "tar",
        ["-czf", archive, "-C", path.join(unpacked, ".."), "tui-frontend"],
        { encoding: "utf8" }
      );
      assert.strictEqual(tar.status, 0, tar.stderr);

      let downloaded = false;
      let extracted = false;
      const dir = await ensureTuiFrontend({
        env: { APEX_TUI_DIR: installDir },
        home: tmp,
        download: async () => {
          downloaded = true;
          return fs.readFileSync(archive);
        },
        extract: (archivePath, destination) => {
          extracted = true;
          extractArchive(archivePath, destination);
        },
        runtime: () => "bun", // bun is on PATH in this environment
        log: () => {},
      });
      assert.strictEqual(downloaded, true);
      assert.strictEqual(extracted, true);
      assert.strictEqual(dir, installDir);
      assert.ok(fs.existsSync(path.join(dir, "package.json")));
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });

  it("fails with a clear error when no runtime is available", async () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "apex-tui-"));
    try {
      const installDir = path.join(tmp, "tui-frontend");
      const staging = fs.mkdtempSync(path.join(os.tmpdir(), "apex-stage-"));
      const archive = path.join(staging, "tui.tar.gz");
      const unpacked = path.join(staging, "unpack", "APEX-dev", "tui-frontend");
      fs.mkdirSync(unpacked, { recursive: true });
      fs.writeFileSync(path.join(unpacked, "package.json"), "{}");

      const { spawnSync } = await import("node:child_process");
      const tar = spawnSync(
        "tar",
        ["-czf", archive, "-C", path.join(unpacked, ".."), "tui-frontend"],
        { encoding: "utf8" }
      );
      assert.strictEqual(tar.status, 0, tar.stderr);

      await assert.rejects(
        ensureTuiFrontend({
          env: { APEX_TUI_DIR: installDir },
          home: tmp,
          download: async () => fs.readFileSync(archive),
          extract: (archivePath, destination) =>
            extractArchive(archivePath, destination),
          runtime: () => null,
          log: () => {},
        }),
        /neither bun nor npm is available/
      );
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });
});
