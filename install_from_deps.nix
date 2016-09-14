{ nixpkgs ? import ./nixpkgs.nix }:

let
  pkgs = import nixpkgs {};
  requirements = pkgs.callPackage ./requirements.nix {};

in requirements
