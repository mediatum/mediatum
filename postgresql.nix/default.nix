{ pkgs ? (import ../nixpkgs.nix {}).pkgs
, lib ? pkgs.lib
, postgresql100 ? pkgs.postgresql100
}:

let

  extra_tsearchData = [
    "unaccent_german_umlauts_special.rules"
  ];


  inherit (lib.trivial) flip;
  inherit (lib.strings) concatMapStrings;

  copy_tsearchData = flip concatMapStrings extra_tsearchData
    (filename: ''

      cp --verbose \
        "${ ./. + "/${filename}"}" \
        "$out/share/tsearch_data/${filename}"
    '')
  ;

in

postgresql100.overrideAttrs ( oldAttrs: {
  postInstall = oldAttrs.postInstall + copy_tsearchData;
})
