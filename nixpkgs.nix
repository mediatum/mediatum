{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-19.09pre184320.eea33299ff7/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
