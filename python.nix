{ pkgs ? (import ./nixpkgs.nix {}).pkgs
, pkgsPy ? (import ./nixpkgs.nix {}).pkgsPy
}:

let

  backend = pkgs.callPackage ./backend.nix { inherit pkgsPy; inherit (pkgsPy) python2; };

in

backend.passthru.python.withPackages
(_: backend.propagatedBuildInputs)
