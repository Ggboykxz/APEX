# shell.nix — APEX dev environment (classique, sans flake)
# Fournit LD_LIBRARY_PATH complet pour Playwright/Chromium + cargo/rustc/gh.
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Playwright chromium dependencies
    glib gtk3 nss nspr atk at-spi2-atk at-spi2-core cairo cups dbus
    expat fontconfig freetype xorg.libxcb xorg.libX11 xorg.libXcomposite
    xorg.libXcursor xorg.libXdamage xorg.libXext xorg.libXfixes
    xorg.libXi xorg.libXrandr xorg.libXrender xorg.libXtst
    xorg.libXinerama xorg.libXScrnSaver libxkbcommon mesa pango alsa-lib
    udev libnotify
    # Toolchains CLI
    cargo rustc gh python3 git curl
  ];

  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath (with pkgs; [
    glib gtk3 nss nspr atk at-spi2-atk at-spi2-core cairo cups dbus
    expat fontconfig freetype xorg.libxcb xorg.libX11 xorg.libXcomposite
    xorg.libXcursor xorg.libXdamage xorg.libXext xorg.libXfixes
    xorg.libXi xorg.libXrandr xorg.libXrender xorg.libXtst
    xorg.libXinerama xorg.libXScrnSaver libxkbcommon mesa pango alsa-lib
    udev libnotify
  ]);
}
