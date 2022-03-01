{ pkgs ? (import ./nixpkgs.nix {}).pkgs
, pkgsPy ? (import ./nixpkgs.nix {}).pkgsPy
}:

let

  backend = pkgs.callPackage ./backend.nix { inherit pkgsPy; inherit (pkgsPy) python2; };
  nginx = pkgs.callPackage ./nginx.nix {};
  postgresql = pkgs.callPackage ./postgresql.nix {};
  uwsgi = pkgs.callPackage ./uwsgi.nix {};

in

pkgsPy.mkShell {
  nativeBuildInputs = [ nginx postgresql uwsgi ];
  inputsFrom = [ backend ];
}
