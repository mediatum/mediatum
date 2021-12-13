{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-19.09pre177248.ed1b59a98e7/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
