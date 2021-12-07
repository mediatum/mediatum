{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-19.03pre157646.f129ed25a04/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
