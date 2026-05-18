{ pkgs ? (import ../nixpkgs.nix {}).pkgs
, lib ? pkgs.lib
, postgresql_18 ? pkgs.postgresql_18
}:

postgresql_18.overrideAttrs ( oldAttrs: {
  postInstall = oldAttrs.postInstall + ''
    install --verbose -D --mode=0644 --no-target-directory "${./unaccent_german_umlauts_special.rules}" "$out/share/postgresql/tsearch_data/unaccent_german_umlauts_special.rules"
  '';

})
