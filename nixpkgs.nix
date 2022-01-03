{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-19.03pre154715.d29947c36a7/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
