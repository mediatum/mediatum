# Generates/returns a mapping like
# "pkgs1803" -> actual pkg set of NixOS 18.03
# so that one can access things like
# `(result of this file).pkgs1803.python27`.

{ system ? builtins.currentSystem }:

let

  urls = rec {
    pkgs = pkgs1803;
    pkgs1803 = https://releases.nixos.org/nixos/18.03/nixos-18.03.132865.411cc559c05/nixexprs.tar.xz;
    pkgs1803a = https://releases.nixos.org/nixos/18.03/nixos-18.03.133402.cb0e20d6db9/nixexprs.tar.xz;
    #pkgs1803 = https://nixos.org/channels/nixos-18.03/nixexprs.tar.xz;
  };

  inherit (builtins) attrNames listToAttrs map;
  mkPkgsPair = name: {
    inherit name;
    value = (import (fetchTarball urls.${name}) {}).pkgs;
  };

in

listToAttrs ( map mkPkgsPair (attrNames urls) )
