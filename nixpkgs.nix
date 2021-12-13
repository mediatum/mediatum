{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-19.09pre185151.7eb6b697014/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
