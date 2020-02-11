{ pkgs ? (import ./nixpkgs.nix {}).pkgs
, lib ? pkgs.lib
, stdenv ? pkgs.stdenv
}:

let

  backend = pkgs.callPackage ./backend.nix {};
  inherit (backend.passthru) dependencies;

in

pkgs.stdenv.mkDerivation {
  name = "mediatumenv";
  propagatedBuildInputs = lib.lists.concatLists [
    dependencies.production
    dependencies.devel
    dependencies.system
  ];
}
