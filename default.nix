{ nixpkgs ? import ./nixpkgs.nix }:

let
  pkgs = import nixpkgs {};
  requirements = pkgs.callPackage ./requirements.nix {};

in pkgs.pythonPackages.buildPythonPackage {
    name = "mediatum";
    propagatedBuildInputs = requirements.production ++ requirements.devel ++ requirements.system;
    buildInputs = requirements.build;
}
