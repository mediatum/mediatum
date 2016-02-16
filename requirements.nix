{fetchurl, fetchgit, stdenv, self, pkgs}:

let
  pythonPackages = pkgs.python27Packages;
  self = pythonPackages;

  ### production deps

  inherit (self) 
  alembic
  decorator
  httplib2
  humanize
  ipython
  jinja2
  ldap 
  lxml
  pillow
  pygments
  pyPdf
  pyyaml
  reportlab
  sympy
  unicodecsv
  werkzeug
  ;

  bibtexparser = self.buildPythonPackage rec {
    name = "bibtexparser-${version}";
    version = "0.6.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/b/bibtexparser/bibtexparser-${version}.tar.gz";
      md5 = "b173b4d1d770dcac929dca2c19ed3f2a";
    };
  };

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

  configargparse = self.buildPythonPackage rec {
    name = "configargparse-${version}";
    version = "0.10.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/C/ConfigArgParse/ConfigArgParse-${version}.tar.gz";
      md5 = "408ad7af06cd449420cecc19bee6f0c9";
    };
    doCheck = false;
  };

  imagemagick = pkgs.imagemagick.override { ghostscript = pkgs.ghostscript; };

  ipaddr = self.buildPythonPackage {
    name = "ipaddr-2.1.11";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/i/ipaddr/ipaddr-2.1.11.tar.gz";
      md5 = "f2c7852f95862715f92e7d089dc3f2cf";
    };
  };

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
    name = "mediatumtal-0.3.2";
    src = fetchurl {
      url = https://pypi.python.org/packages/source/m/mediatumtal/mediatumtal-0.3.2.tar.gz;
      md5 = "c41902f1a9a60237640d3a730c58f05f";
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

  parcon = self.buildPythonPackage {
    name = "parcon-0.1.25";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/parcon/parcon-0.1.25.tar.gz";
      md5 = "146ab4d138fd5b1848390fbf199c3ac2";
    };
  };

  prettytable = self.buildPythonPackage {
    name = "prettytable-0.7.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/PrettyTable/prettytable-0.7.2.tar.bz2";
      md5 = "760dc900590ac3c46736167e09fa463a";
    };
  };

  psycopg2 = self.buildPythonPackage {
    name = "psycopg2-2.6.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/psycopg2/psycopg2-2.6.1.tar.gz";
      md5 = "842b44f8c95517ed5b792081a2370da1";
    };
    propagatedBuildInputs = with self; [pkgs.postgresql94];
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

  python-logstash = self.buildPythonPackage {
    name = "python-logstash-0.4.5";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/python-logstash/python-logstash-0.4.5.tar.gz";
      md5 = "401462a61563f992894bd65c976e556b";
    };
  };

  requests = self.requests2;
  
  scrypt = self.buildPythonPackage {
    name = "scrypt-0.7.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/s/scrypt/scrypt-0.7.1.tar.gz";
      md5 = "9feb713f183e11caa940e8ec71cf1361";
    };
    propagatedBuildInputs = with self; [pkgs.openssl];
    
    doCheck = false;
  };

  sqlalchemy = self.sqlalchemy_1_0;

  sqlalchemy-utils = self.buildPythonPackage {
    name = "SQLAlchemy-Utils-0.31.4";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/S/SQLAlchemy-Utils/SQLAlchemy-Utils-0.31.4.tar.gz";
      md5 = "6134419c599dbc378452b5f9d4ceb5db";
    };
    propagatedBuildInputs = with self; [six sqlalchemy_1_0];
  };

  sqlalchemy-continuum = self.buildPythonPackage {
    name = "sqlalchemy-continuum-1.2.2";

    src = fetchgit {
      url = https://github.com/mediatum/sqlalchemy-continuum.git;
      rev = "a30c17a2dcdf58866265f698e05423d2225d5f23";
      sha256 = "189a52c4d6425ae6dd2894c95eaa7685eda5cf78622b13da9a18805cdf3cfcca";
    };

    propagatedBuildInputs = with self; [sqlalchemy sqlalchemy-utils];
  };

  ### test /devel deps

  inherit (self)
  mock
  munch
  py
  pytest
  redis
  ;

  fake-factory = self.buildPythonPackage {
    name = "fake-factory-0.5.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/f/fake-factory/fake-factory-0.5.2.tar.gz";
      md5 = "c32835b3fed1f18bb8aad12527cc1941";
    };
    doCheck = false;
  };

  factory-boy = self.buildPythonPackage {
    name = "factory-boy";
    src = fetchgit {
      url = https://github.com/dpausp/factory_boy;
      rev = "8e5a74651008f1eb0f6bf4f03bf96d7e33ce6314";
      sha256 = "12dced99cb13c05c11448d15137cccef170b923e501eceb3cbe2c2bac8f6096b";
    };
    propagatedBuildInputs = with self; [fake-factory];
    buildInputs = with self; [mock];
  };

  pytest-capturelog = self.buildPythonPackage {
    name = "pytest-capturelog-0.7";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pytest-capturelog/pytest-capturelog-0.7.tar.gz";
      md5 = "cfeac23d8ed254deaeb50a8c0aa141e9";
    };
    propagatedBuildInputs = with self; [py];
  };

  redis-collections = self.buildPythonPackage {
    name = "redis-collections-0.1.7";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/r/redis-collections/redis-collections-0.1.7.tar.gz";
      md5 = "67aa817d9a2f1f63b3b3251062762e7d";
    };
    propagatedBuildInputs = with self; [redis];
  };


in {
  production = [
      # python deps
      alembic
      bibtexparser
      coffeescript
      configargparse
      decorator
      httplib2
      humanize
      ipaddr
      ipython
      ipython-sql
      jinja2
      lxml
      mediatumbabel
      mediatumfsm
      mediatumtal
      mollyZ3950
      parcon
      pillow
      ldap
      psycopg2
      pyaml
      pydot2
      pyexiftool
      pygments
      pyjade
      pymarc
      pympler
      pyPdf
      python-Levenshtein
      python-logstash
      pyyaml
      reportlab
      requests
      scrypt
      sqlalchemy
      sqlalchemy-continuum
      sqlalchemy-utils
      sympy
      unicodecsv
      werkzeug
      # other
      pkgs.ffmpeg
      imagemagick
      pkgs.graphviz-nox
      pkgs.perlPackages.ImageExifTool
      pkgs.poppler_utils
    ];

    devel = [
      factory-boy
      mock
      munch
      pytest
      pytest-capturelog
      redis-collections
      pkgs.redis
    ];

    system = with pkgs; [
      git
      nginx
      zsh
    ];

    build = [ pythonPackages.setuptools-git ];
}
