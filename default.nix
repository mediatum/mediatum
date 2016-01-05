let
  pkgs = import <nixpkgs> {};
  requirements = pkgs.callPackage ./requirements.nix {};

in

pkgs.pythonPackages.buildPythonPackage {
    name = "mediatum";
    src = ./.;
    propagatedBuildInputs = requirements.production ++ requirements.devel ++ requirements.system;
    buildInputs = requirements.build;
}
