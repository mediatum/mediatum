{ pkgs ? (import ./nixpkgs.nix {}).pkgs }:

let

  backend = pkgs.callPackage ./backend.nix {};

in

pkgs.mkShell { inputsFrom = [ backend ]; }
