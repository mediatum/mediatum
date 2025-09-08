{ pkgs ? (import ../nixpkgs.nix {}).pkgs
, pkgsPy ? (import ../nixpkgs.nix {}).pkgsPy
, lib ? pkgs.lib
, python2 ? pkgsPy.python2
}:

let

  python =
    # Each file in `python-packages` is treated as a package.
    # The name of the package is the filename (minus `.nix`).
    let
      # Create list of package names from file listing.
      pkgNames =
        (builtins.map lib.lists.head
        (builtins.map (builtins.match "(.+)\\.nix")
        (lib.attrsets.attrNames
        (builtins.readDir ./python-packages
      ))));
      # This returns a path to the package file of given name.
      mkPkgPath = name: ./python-packages + "/${name}.nix";
      # This is the function that actually evaluates the
      # package files.  It is used by nixpkgs' python package
      # repository to extend itself with our packages.
      packageOverrides = new: old:
          lib.attrsets.genAttrs pkgNames
          (name: old.callPackage (mkPkgPath name) {});
    in
      python2.override { inherit packageOverrides; };

  propagatedBuildInputs = lib.attrsets.attrValues {
    inherit (python.pkgs)
      ConfigArgParse
      alembic
      attrs
      bibtexparser
      coffeescript
      decorator
      exifread_2_3_2
      fdfgen
      flask-admin
      flask_login
      httplib2
      humanize
      ipaddr
      ipdb
      jinja2
      ldap
      lrucache-1-6-1
      lxml
      magic
      mediatumfsm
      mediatumtal
      munch
      mutagen
      parcon
      pillow
      polib
      psycopg2
      py_scrypt
      pydot2
      pyexiftool
      pygments
      pyjade
      pyyaml
      requests
      ruamel_yaml
      sqlalchemy
      sqlalchemy-continuum
      sqlalchemy-utils
      sympy
      unicodecsv
      werkzeug
    ;
    graphicsmagick = pkgs.graphicsmagick.overrideAttrs
      (oldAttrs: oldAttrs // {
        buildInputs = oldAttrs.buildInputs ++ [ pkgs.lcms2 ];
      });
    inherit (pkgs)
      ffmpeg
      glibcLocales
      graphviz-nox
      pdftk
      poppler_utils
    ;
    icu = pkgs.icu.dev;
    inherit (pkgs.perlPackages) ImageExifTool;
  };

in

python.pkgs.buildPythonApplication {
  name = "mediatum-backend";
  src = ./../.;
  nativeBuildInputs = [ python.pkgs.setuptools-git ];
  inherit propagatedBuildInputs;
  passthru = { inherit python; };
}
