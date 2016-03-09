{ nixpkgs ? import ./nixpkgs.nix }:

let
  pkgs = import nixpkgs {};
  requirements = pkgs.callPackage ./requirements.nix {};

in pkgs.stdenv.mkDerivation {
    name = "mediatumenv";
    propagatedBuildInputs = requirements.production ++ requirements.devel ++ requirements.system;
}

