{ pkgs ? (import ../nixpkgs.nix {}).pkgs
, lib ? pkgs.lib
, postgresql_15 ? pkgs.postgresql_15
}:

postgresql_15.overrideAttrs ( oldAttrs: {
  postInstall = oldAttrs.postInstall + ''
    install --verbose -D --mode=0644 --no-target-directory "${./unaccent_german_umlauts_special.rules}" "$out/share/postgresql/tsearch_data/unaccent_german_umlauts_special.rules"
  '';

})
