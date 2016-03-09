{fetchurl, fetchgit, stdenv, self, pkgs}:

let
  pythonPackages = pkgs.python27Packages;
  self = pythonPackages;

  ### production deps

  inherit (self) 
  httplib2
  humanize
  ipdb
  ipython
  jinja2
  ldap 
  lxml
  pillow
  pygments
  pyPdf
  pyyaml
  reportlab
  sqlite3
  werkzeug
  ;

  coffeescript = self.buildPythonPackage rec {
    name = "coffeescript-${version}";
    version = "1.1.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/C/CoffeeScript/CoffeeScript-${version}.tar.gz";
      md5 = "9ae342ac4c7b383841b58b3da14bec8b";
    };
    propagatedBuildInputs = with self; [PyExecJS];
    doCheck = false;
  };

  imagemagick = pkgs.imagemagick.override { ghostscript = pkgs.ghostscript; };

  ipython-sql = self.buildPythonPackage {
    name = "ipython-sql-0.3.6";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/i/ipython-sql/ipython-sql-0.3.6.tar.gz";
      md5 = "d4feb00ac5806d7640b2545a43974766";
    };
    propagatedBuildInputs = with self; [prettytable ipython sqlalchemy sqlparse six];
  };

  mediatumbabel = self.buildPythonPackage {
    name = "mediatumbabel-0.1.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/m/mediatumbabel/mediatumbabel-0.1.1.tar.gz";
      md5 = "1d3cf44fc51b0a194853375f32968901";
    };
    propagatedBuildInputs = with self; [Babel];
    buildInputs = with self; [setuptools-git];
  };

  mediatumfsm = self.buildPythonPackage {
    name = "mediatumfsm-0.1";
    src = fetchurl {
      url = https://pypi.python.org/packages/source/m/mediatumfsm/mediatumfsm-0.1.tar.gz;
      md5 = "38987e3500a2fd05034b4e86f7817fe6";
    };
    propagatedBuildInputs = with self; [pydot2];
    buildInputs = with self; [setuptools-git];
  };

  mediatumtal = self.buildPythonPackage {
    name = "mediatumtal-0.1.1";
    src = fetchgit {
      url = https://github.com/mediatum/mediatumtal;
      rev = "dbbd2095d637d9d5cf5e4e7b74ce6a23baa662f5";
      sha256 = "9bb00833f5e800fc4ec93bc058a0660e602040c5474d8d3d56cc58f6678f9941";
    };
  };

  mollyZ3950 = self.buildPythonPackage {
    name = "mollyZ3950-2.04-molly1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/m/mollyZ3950/mollyZ3950-2.04-molly1.tar.gz";
      md5 = "a0e5d7bb395ae31026afc7f974711630";
    };
    propagatedBuildInputs = with self; [ply];
  };

  prettytable = self.buildPythonPackage {
    name = "prettytable-0.7.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/PrettyTable/prettytable-0.7.2.tar.bz2";
      md5 = "760dc900590ac3c46736167e09fa463a";
    };
  };

  pyaml = self.buildPythonPackage rec {
    name = "pyaml-${version}";
    version = "15.8.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pyaml/pyaml-${version}.tar.gz";
      md5 = "e3a39e02dffaf5f6efa8ccdd22745739";
    };
    propagatedBuildInputs = with self; [pyyaml];
  };

  pydot2 = self.buildPythonPackage {
    name = "pydot2-1.0.33";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pydot2/pydot2-1.0.33.tar.gz";
      md5 = "33ddc024f5f3df4522ab2d867bdedb0d";
    };
    propagatedBuildInputs = with self; [pyparsing setuptools];
  };

  PyExecJS = self.buildPythonPackage {
    name = "PyExecJS-1.1.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/PyExecJS/PyExecJS-1.1.0.zip";
      md5 = "027bcbc0a2f44419a6be1e3c4d5d68a1";
    };
    doCheck = false;
  };

  pyexiftool = self.buildPythonPackage {
    name = "pyexiftool-0.1";

    src = fetchgit {
      url = https://github.com/smarnach/pyexiftool;
      rev = "3db3764895e687d75b42d3ae4e554ca8664a7f6f";
      sha256 = "f3f3b8e9a48846c5610006e5131ed4029bafc95b67a9864f1fcfeb45d8c2facb";
    };
  };

  pyjade = self.buildPythonPackage {
    name = "pyjade-3.1.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pyjade/pyjade-3.1.0.tar.gz";
      md5 = "e6a38f7c5c4f6fdee15800592a85eb1d";
    };
    propagatedBuildInputs = with self; [six];
    doCheck = false;
  };

  pymarc = self.buildPythonPackage rec {
    name = "pymarc-${version}";
    version = "3.1.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pymarc/pymarc-${version}.tar.gz";
      md5 = "78c1eecad2e7ed8b2a72b6e37c5e9363";
    };
    propagatedBuildInputs = with self; [six];
  };
  
  pympler = self.buildPythonPackage {
    name = "pympler-0.4.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/Pympler/Pympler-0.4.2.tar.gz";
      md5 = "6bdfd913ad4c94036e8a2b358e49abd7";
    };
    doCheck = false;
  };

  pyparsing = self.buildPythonPackage rec {
    name = "pyparsing-${version}";
    version = "2.0.7";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pyparsing/pyparsing-${version}.tar.gz";
      md5 = "1c8bed7530642ca19197f3caa05fd28b";
    };
  };

  python-Levenshtein = self.buildPythonPackage {
    name = "python-Levenshtein-0.12.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/python-Levenshtein/python-Levenshtein-0.12.0.tar.gz";
      md5 = "e8cde197d6d304bbdc3adae66fec99fb";
    };
    propagatedBuildInputs = with self; [setuptools];
  };

  requests = self.requests2;
  
  sqlalchemy = self.sqlalchemy_1_0;

  ### test /devel deps

  inherit (self)
  mock
  munch
  py
  pytest
  redis
  ;

in {
  production = [
      # python deps
      coffeescript
      httplib2
      humanize
      ipdb
      ipython
      ipython-sql
      jinja2
      lxml
      mediatumbabel
      mediatumfsm
      mediatumtal
      mollyZ3950
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
      python-Levenshtein
      pyyaml
      reportlab
      requests
      sqlalchemy
      sqlite3
      werkzeug
      # other
      pkgs.ffmpeg
      imagemagick
      pkgs.graphviz-nox
      pkgs.perlPackages.ImageExifTool
      pkgs.poppler_utils
      pkgs.pythonPackages.MySQL_python
    ];

    devel = [
      mock
      munch
      pytest
      pkgs.pythonPackages.msgpack
    ];

    system = with pkgs; [
      git
      nginx
      zsh
    ];

    build = [ pythonPackages.setuptools-git ];
}
