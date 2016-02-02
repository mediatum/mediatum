{ nixpkgs ? https://nixos.org/releases/nixos/unstable/nixos-16.03pre75806.77f8f35/ }:

let
  pkgs = import nixpkgs {};
  requirements = pkgs.callPackage ./requirements.nix {};

in

pkgs.pythonPackages.buildPythonPackage {
    name = "mediatum";
    src = ./.;
    propagatedBuildInputs = requirements.production ++ requirements.devel ++ requirements.system;
    buildInputs = requirements.build;
}
