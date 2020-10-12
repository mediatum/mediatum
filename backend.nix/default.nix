{ pkgs ? (import ../nixpkgs.nix {}).pkgs
, lib ? pkgs.lib
, python ? pkgs.python2
}:

let

  pythonSuper = python;

in let

  inherit (import ../nixpkgs.nix {}) pkgs1803a;

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
      pythonSuper.override { inherit packageOverrides; };

  propagatedBuildInputs = lib.attrsets.attrValues {
    inherit (python.pkgs)
      ConfigArgParse
      alembic
      attrs_18
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
      ipython
      ipython-sql
      jinja2
      ldap
      lrucache-1-6-1
      lxml
      magic
      mediatumfsm
      mediatumtal
      munch
      mutagen
      mollyZ3950
      parcon
      pillow
      psycopg2
      pyPdf
      py_scrypt
      pyaml
      pydot2
      pyexiftool
      pygeoip
      pygments
      pyjade
      pymarc
      pympler
      python-logstash
      pyyaml
      reportlab
      requests
      sqlalchemy
      sqlalchemy-continuum
      sqlalchemy-utils
      sympy
      unicodecsv
      werkzeug
    ;
    inherit (pkgs)
      ffmpeg
      glibcLocales
      graphviz-nox
      icu
      pdftk
      poppler_utils
    ;
    inherit (pkgs1803a) ghostscript graphicsmagick;
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
