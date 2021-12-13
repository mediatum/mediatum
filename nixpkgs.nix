{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-19.09pre189146.c2742295fb1/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
