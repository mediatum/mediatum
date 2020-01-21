{ pkgs ? (import ./nixpkgs.nix {}).pkgs
, nginx ? pkgs.nginx
}:

nginx
