{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-19.09pre182571.e829aeefa35/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
