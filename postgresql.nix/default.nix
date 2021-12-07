{ pkgs ? (import ../nixpkgs.nix {}).pkgs
, lib ? pkgs.lib
, postgresql_10 ? pkgs.postgresql_10
}:

postgresql_10.overrideAttrs ( oldAttrs: {
  postInstall = oldAttrs.postInstall + ''
    install --verbose -D --mode=0644 --no-target-directory "${./unaccent_german_umlauts_special.rules}" "$out/share/tsearch_data/unaccent_german_umlauts_special.rules"
  '';

})
