# Shell Nix pour l'environnement de développement APEX
# Fournit les dépendances système manquantes :
#   - libglib + GTK + NSS (pour Playwright chromium)
#   - cargo/rustc (pour les tests Rust)
#   - gh CLI (pour les tests GitHub)
{
  description = "APEX dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          # Playwright chromium dependencies
          glib
          gtk3
          nss
          nspr
          atk
          at-spi2-atk
          at-spi2-core
          cairo
          cups
          dbus
          expat
          fontconfig
          freetype
          xorg.libxcb
          xorg.libX11
          xorg.libXcomposite
          xorg.libXcursor
          xorg.libXdamage
          xorg.libXext
          xorg.libXfixes
          xorg.libXi
          xorg.libXrandr
          xorg.libXrender
          xorg.libXtst
          xorg.libXinerama
          xorg.libXScrnSaver
          libxkbcommon
          mesa
          pango
          alsa-lib
          # Rust toolchain
          cargo
          rustc
          # GitHub CLI
          gh
          # Utilitaires
          git
          curl
          python3
        ];

        # Exposer les librairies au linker
        LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
          pkgs.glib pkgs.gtk3 pkgs.nss pkgs.nspr pkgs.atk
          pkgs.at-spi2-atk pkgs.at-spi2-core pkgs.cairo pkgs.cups
          pkgs.dbus pkgs.expat pkgs.fontconfig pkgs.freetype
          pkgs.xorg.libxcb pkgs.xorg.libX11 pkgs.xorg.libXcomposite
          pkgs.xorg.libXcursor pkgs.xorg.libXdamage pkgs.xorg.libXext
          pkgs.xorg.libXfixes pkgs.xorg.libXi pkgs.xorg.libXrandr
          pkgs.xorg.libXrender pkgs.xorg.libXtst pkgs.xorg.libXinerama
          pkgs.xorg.libXScrnSaver pkgs.libxkbcommon pkgs.mesa
          pkgs.pango pkgs.alsa-lib
        ];
      };
    };
}
