{ pkgs ? (import ./nixpkgs.nix {}).pkgs
, acme-sh ? pkgs.acme-sh
}:

acme-sh
