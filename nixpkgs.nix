{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-20.03pre192735.bd61f91fd10/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
