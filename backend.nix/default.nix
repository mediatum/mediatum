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

  dependencies.production =
    (with (python.pkgs); [
      alembic
      attrs_18
      bibtexparser
      coffeescript
      ConfigArgParse
      decorator
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
      lxml
      magic
      mediatumfsm
      mediatumtal
      mollyZ3950
      parcon
      pillow
      ldap
      pyaml
      pydot2
      pyexiftool
      pygments
      pyjade
      pymarc
      pympler
      pyPdf
      python-logstash
      pyyaml
      reportlab
      requests
      psycopg2
      py_scrypt
      sqlalchemy
      sqlalchemy-continuum
      sqlalchemy-utils
      sympy
      unicodecsv
      werkzeug
    ]) ++ (with pkgs; [
      ffmpeg
      pkgs1803a.ghostscript
      pkgs1803a.graphicsmagick
      graphviz-nox
      icu
      pdftk
      poppler_utils
      glibcLocales
    ]) ++ [
      pkgs.perlPackages.ImageExifTool
      (pkgs.callPackage ../uwsgi.nix {})
      (pkgs.callPackage ../postgresql.nix {})
      (pkgs.callPackage ../nginx.nix {})
    ];

  dependencies.devel = (with python.pkgs; [
      ipykernel
      munch
    ]);

in

python.pkgs.buildPythonApplication {
  name = "mediatum-backend";
  src = ./../.;
  passthru = {
    inherit dependencies;
    python = python;
  };
  nativeBuildInputs = [ python.pkgs.setuptools-git ];
  propagatedBuildInputs = lib.lists.concatLists [
    dependencies.production
    dependencies.devel
  ];
}
