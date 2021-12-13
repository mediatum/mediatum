{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-19.09pre170721.e52396ce2c0/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
