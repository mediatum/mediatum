{ pkgs ? (import ./nixpkgs.nix {}).pkgs
, uwsgi ? pkgs.uwsgi
}:

let

  uwsgi1 = uwsgi.override { plugins = [ "python2" ]; };

in

uwsgi1.overrideAttrs ( oldAttrs: oldAttrs // {
  configurePhase = oldAttrs.configurePhase + ''
    sed --regexp-extended 's,^yaml.*$,yaml = true,g' --in-place buildconf/nixos.ini
  '';
})
