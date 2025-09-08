{ system ? builtins.currentSystem }:

let

  urls = {
    pkgs   = https://releases.nixos.org/nixpkgs/nixpkgs-25.11pre805949.bdac72d387dc/nixexprs.tar.xz;
    pkgsPy = https://releases.nixos.org/nixpkgs/nixpkgs-20.03pre197736.91d5b3f07d2/nixexprs.tar.xz;
    pkgsUwsgi = https://releases.nixos.org/nixpkgs/nixpkgs-22.05pre363272.4d600814942/nixexprs.tar.xz;
  };

  inherit (builtins) attrNames listToAttrs map;

  mkPkgsPair = name: {
    inherit name;
    value = import (fetchTarball urls.${name}) { inherit system; };
  };

in

listToAttrs ( map mkPkgsPair (attrNames urls) )
