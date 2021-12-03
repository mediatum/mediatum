{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixos/18.03/nixos-18.03.133402.cb0e20d6db9/nixexprs.tar.xz;
in

(import (fetchTarball url) {inherit system; }).pkgs
