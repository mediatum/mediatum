{ pkgs ? (import ./nixpkgs.nix {}).pkgs }:

let

  backend = pkgs.callPackage ./backend.nix {};
  inherit (backend.passthru) dependencies python;

in

python.buildEnv.override {
  extraLibs = dependencies.production ++ dependencies.devel;
  ignoreCollisions = true;
}
