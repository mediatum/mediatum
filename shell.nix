{ pkgs ? (import ./nixpkgs.nix {}).pkgs }:

let
  requirements = pkgs.callPackage ./requirements.nix {};

in pkgs.stdenv.mkDerivation {
    name = "mediatumenv";
    propagatedBuildInputs = requirements.production ++ requirements.devel ++ requirements.system;
}

