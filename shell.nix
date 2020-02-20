{ pkgs ? (import ./nixpkgs.nix {}).pkgs }:

let

  backend = pkgs.callPackage ./backend.nix {};
  nginx = pkgs.callPackage ./nginx.nix {};
  postgresql = pkgs.callPackage ./postgresql.nix {};
  uwsgi = pkgs.callPackage ./uwsgi.nix {};

in

pkgs.mkShell {
  nativeBuildInputs = [ nginx postgresql uwsgi ];
  inputsFrom = [ backend ];
}
