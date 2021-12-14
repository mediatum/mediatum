{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-20.03pre197736.91d5b3f07d2/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
