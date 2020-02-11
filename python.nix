{ pkgs ? (import ./nixpkgs.nix {}).pkgs }:

let

  backend = pkgs.callPackage ./backend.nix {};

in

backend.passthru.python.buildEnv.override {
  extraLibs = backend.propagatedBuildInputs;
  ignoreCollisions = true;
}
