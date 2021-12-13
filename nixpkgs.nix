{ system ? builtins.currentSystem }:

let

  url = https://releases.nixos.org/nixpkgs/nixpkgs-19.03pre161557.34efe45ef8b/nixexprs.tar.xz;

in

(import (fetchTarball url) {inherit system; }).pkgs
