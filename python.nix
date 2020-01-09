{ pkgs ? (import ./nixpkgs.nix {}).pkgs }:

let
  requirements = pkgs.callPackage ./requirements.nix {};

in pkgs.python.buildEnv.override {
    extraLibs = requirements.production ++ requirements.devel;
    ignoreCollisions = true;
}
