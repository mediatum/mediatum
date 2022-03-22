{ system ? builtins.currentSystem }:

let

  urls = {
    pkgs   = https://releases.nixos.org/nixpkgs/nixpkgs-22.05pre336340.cdaa4ce25b7/nixexprs.tar.xz;
    pkgsPy = https://releases.nixos.org/nixpkgs/nixpkgs-20.03pre197736.91d5b3f07d2/nixexprs.tar.xz;
  };

  inherit (builtins) attrNames listToAttrs map;

  mkPkgsPair = name: {
    inherit name;
    value = import (fetchTarball urls.${name}) { inherit system; };
  };

in

listToAttrs ( map mkPkgsPair (attrNames urls) )
