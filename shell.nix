let
  pkgs = import <nixpkgs> {};
  requirements = pkgs.callPackage ./requirements.nix {};

in

pkgs.stdenv.mkDerivation {
    name = "mediatumenv";
    src = ./.;
    propagatedBuildInputs = requirements.production ++ requirements.devel ++ requirements.system;
}

