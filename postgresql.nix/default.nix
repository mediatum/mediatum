{ pkgs ? (import ../nixpkgs.nix {}).pkgs
, lib ? pkgs.lib
, postgresql_17 ? pkgs.postgresql_17
}:

postgresql_17.overrideAttrs ( oldAttrs: {
  postInstall = oldAttrs.postInstall + ''
    install --verbose -D --mode=0644 --no-target-directory "${./unaccent_german_umlauts_special.rules}" "$out/share/postgresql/tsearch_data/unaccent_german_umlauts_special.rules"
  '';

})
