{ pkgs ? (import ./nixpkgs.nix {}).pkgs }:

let

  backend = pkgs.callPackage ./backend.nix {};

in

backend.passthru.python.withPackages
(_: backend.propagatedBuildInputs)
