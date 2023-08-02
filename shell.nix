{ pkgs ? (import ./nixpkgs.nix {}).pkgs
, pkgsPy ? (import ./nixpkgs.nix {}).pkgsPy
, pkgsUwsgi ? (import ./nixpkgs.nix {}).pkgsUwsgi
}:

let

  backend = pkgs.callPackage ./backend.nix { inherit pkgsPy; inherit (pkgsPy) python2; };
  acme-sh = pkgs.callPackage ./acme-sh.nix {};
  nginx = pkgs.callPackage ./nginx.nix {};
  postgresql = pkgs.callPackage ./postgresql.nix {};
  uwsgi = pkgsUwsgi.callPackage ./uwsgi.nix {};

in

pkgsPy.mkShell {
  nativeBuildInputs = [ acme-sh nginx postgresql uwsgi ];
  inputsFrom = [ backend ];
}
