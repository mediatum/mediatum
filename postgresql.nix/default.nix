{ pkgs ? (import ../nixpkgs.nix {}).pkgs
, lib ? pkgs.lib
, postgresql_14 ? pkgs.postgresql_14
}:

postgresql_14.overrideAttrs ( oldAttrs: {
  postInstall = oldAttrs.postInstall + ''
    install --verbose -D --mode=0644 --no-target-directory "${./unaccent_german_umlauts_special.rules}" "$out/share/postgresql/tsearch_data/unaccent_german_umlauts_special.rules"
  '';

})
