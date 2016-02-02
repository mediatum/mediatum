{fetchurl, fetchgit, stdenv, self, pkgs}:

let
  pythonPackages = pkgs.python27Packages;
  self = pythonPackages;

  ### production deps

  # transitive production deps
  inherit (self)
  Babel
  funcsigs
  markupsafe
  ply
  pytz
  setuptools-git
  six
  sqlparse
  ;

  # direct production deps
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
  requests
  sympy
  unicodecsv
  werkzeug
  ;

  sqlalchemy = self.sqlalchemy_1_0;

  bibtexparser = self.buildPythonPackage {
    name = "bibtexparser-0.6.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/b/bibtexparser/bibtexparser-0.6.1.tar.gz";
      md5 = "9e1fa92ac059c6a75f7076965267c3f8";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  coffeescript = self.buildPythonPackage {
    name = "coffeescript-1.1.1";
    src = fetchurl {
      url = https://pypi.python.org/packages/source/C/CoffeeScript/CoffeeScript-1.1.1.tar.gz;
      md5 = "7c7083dc51e104fb89fe55b674314c2a";
    };
    propagatedBuildInputs = with self; [PyExecJS];
    buildInputs = with self; [];
    doCheck = false;
  };

  configargparse = self.buildPythonPackage {
    name = "configargparse-0.9.3";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/C/ConfigArgParse/ConfigArgParse-0.9.3.tar.gz";
      md5 = "69273e8099661cd12985b85d795ab73e";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  imagemagick = pkgs.imagemagick.override { ghostscript = pkgs.ghostscript; };

  ipaddr = self.buildPythonPackage {
    name = "ipaddr-2.1.11";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/i/ipaddr/ipaddr-2.1.11.tar.gz";
      md5 = "f2c7852f95862715f92e7d089dc3f2cf";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  ipython-sql = self.buildPythonPackage {
    name = "ipython-sql-0.3.6";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/i/ipython-sql/ipython-sql-0.3.6.tar.gz";
      md5 = "d4feb00ac5806d7640b2545a43974766";
    };
    propagatedBuildInputs = with self; [prettytable ipython sqlalchemy sqlparse six];
    buildInputs = with self; [];
    doCheck = false;
  };

  mediatumbabel = self.buildPythonPackage {
    name = "mediatumbabel-0.1.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/m/mediatumbabel/mediatumbabel-0.1.1.tar.gz";
      md5 = "1d3cf44fc51b0a194853375f32968901";
    };
    propagatedBuildInputs = with self; [Babel];
    buildInputs = with self; [setuptools-git];
    doCheck = false;
  };

  mediatumfsm = self.buildPythonPackage {
    name = "mediatumfsm-0.1";
    src = fetchurl {
      url = https://pypi.python.org/packages/source/m/mediatumfsm/mediatumfsm-0.1.tar.gz;
      md5 = "38987e3500a2fd05034b4e86f7817fe6";
    };
    propagatedBuildInputs = with self; [pydot2];
    buildInputs = with self; [setuptools-git];
    doCheck = false;
  };

  mediatumtal = self.buildPythonPackage {
    name = "mediatumtal-0.3.2";
    src = fetchurl {
      url = https://pypi.python.org/packages/source/m/mediatumtal/mediatumtal-0.3.2.tar.gz;
      md5 = "c41902f1a9a60237640d3a730c58f05f";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  mollyZ3950 = self.buildPythonPackage {
    name = "mollyZ3950-2.04-molly1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/m/mollyZ3950/mollyZ3950-2.04-molly1.tar.gz";
      md5 = "a0e5d7bb395ae31026afc7f974711630";
    };
    propagatedBuildInputs = with self; [ply];
    buildInputs = with self; [];
    doCheck = false;
  };

  parcon = self.buildPythonPackage {
    name = "parcon-0.1.25";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/parcon/parcon-0.1.25.tar.gz";
      md5 = "146ab4d138fd5b1848390fbf199c3ac2";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  prettytable = self.buildPythonPackage {
    name = "prettytable-0.7.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/PrettyTable/prettytable-0.7.2.tar.bz2";
      md5 = "760dc900590ac3c46736167e09fa463a";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  psycopg2 = self.buildPythonPackage {
    name = "psycopg2-2.6.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/psycopg2/psycopg2-2.6.1.tar.gz";
      md5 = "842b44f8c95517ed5b792081a2370da1";
    };
    propagatedBuildInputs = with self; [pkgs.postgresql94];
    buildInputs = with self; [];
    doCheck = false;
  };

  pyaml = self.buildPythonPackage {
    name = "pyaml-15.6.3";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pyaml/pyaml-15.6.3.tar.gz";
      md5 = "36a769535f45c2d04feb9ba50cfbbd3d";
    };
    propagatedBuildInputs = with self; [pyyaml];
    buildInputs = with self; [];
    doCheck = false;
  };

  pydot2 = self.buildPythonPackage {
    name = "pydot2-1.0.33";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pydot2/pydot2-1.0.33.tar.gz";
      md5 = "33ddc024f5f3df4522ab2d867bdedb0d";
    };
    propagatedBuildInputs = with self; [pyparsing setuptools];
    buildInputs = with self; [];
    doCheck = false;
  };

  PyExecJS = self.buildPythonPackage {
    name = "PyExecJS-1.1.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/PyExecJS/PyExecJS-1.1.0.zip";
      md5 = "027bcbc0a2f44419a6be1e3c4d5d68a1";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  pyexiftool = self.buildPythonPackage {
    name = "pyexiftool-0.1";

    src = fetchgit {
      url = https://github.com/smarnach/pyexiftool;
      rev = "3db3764895e687d75b42d3ae4e554ca8664a7f6f";
      sha256 = "f3f3b8e9a48846c5610006e5131ed4029bafc95b67a9864f1fcfeb45d8c2facb";
    };

    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  pyjade = self.buildPythonPackage {
    name = "pyjade-3.1.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pyjade/pyjade-3.1.0.tar.gz";
      md5 = "e6a38f7c5c4f6fdee15800592a85eb1d";
    };
    propagatedBuildInputs = with self; [six];
    buildInputs = with self; [];
    doCheck = false;
  };

  pymarc = self.buildPythonPackage {
    name = "pymarc-3.0.4";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pymarc/pymarc-3.0.4.tar.gz";
      md5 = "8d6fe584820542760b2f954076fba9aa";
    };
    propagatedBuildInputs = with self; [six];
    buildInputs = with self; [];
    doCheck = false;
  };
  
  pympler = self.buildPythonPackage {
    name = "pympler-0.4.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/Pympler/Pympler-0.4.2.tar.gz";
      md5 = "6bdfd913ad4c94036e8a2b358e49abd7";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  pyparsing = self.buildPythonPackage {
    name = "pyparsing-2.0.3";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pyparsing/pyparsing-2.0.3.zip";
      md5 = "0a5ec41bb650aed802751a311b5d820d";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  python-Levenshtein = self.buildPythonPackage {
    name = "python-Levenshtein-0.12.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/python-Levenshtein/python-Levenshtein-0.12.0.tar.gz";
      md5 = "e8cde197d6d304bbdc3adae66fec99fb";
    };
    propagatedBuildInputs = with self; [setuptools];
    buildInputs = with self; [];
    doCheck = false;
  };

  python-logstash = self.buildPythonPackage {
    name = "python-logstash-0.4.5";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/python-logstash/python-logstash-0.4.5.tar.gz";
      md5 = "401462a61563f992894bd65c976e556b";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  scrypt = self.buildPythonPackage {
    name = "scrypt-0.7.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/s/scrypt/scrypt-0.7.1.tar.gz";
      md5 = "9feb713f183e11caa940e8ec71cf1361";
    };
    propagatedBuildInputs = with self; [pkgs.openssl];
    buildInputs = with self; [];
    doCheck = false;
  };

  sqlalchemy-utils = self.buildPythonPackage {
    name = "SQLAlchemy-Utils-0.31.4";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/S/SQLAlchemy-Utils/SQLAlchemy-Utils-0.31.4.tar.gz";
      md5 = "6134419c599dbc378452b5f9d4ceb5db";
    };
    propagatedBuildInputs = with self; [six sqlalchemy_1_0];
    buildInputs = with self; [];
    doCheck = false;
  };

  sqlalchemy-continuum = self.buildPythonPackage {
    name = "sqlalchemy-continuum-1.2.2";

    src = fetchgit {
      url = https://github.com/mediatum/sqlalchemy-continuum.git;
      rev = "a30c17a2dcdf58866265f698e05423d2225d5f23";
      sha256 = "189a52c4d6425ae6dd2894c95eaa7685eda5cf78622b13da9a18805cdf3cfcca";
    };

    propagatedBuildInputs = with self; [sqlalchemy sqlalchemy-utils];
    buildInputs = with self; [];
    doCheck = false;
  };

  ### test /devel deps

  inherit (self)
  mock
  munch
  pytest
  redis
  ;

  fake-factory = self.buildPythonPackage {
    name = "fake-factory-0.5.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/f/fake-factory/fake-factory-0.5.2.tar.gz";
      md5 = "c32835b3fed1f18bb8aad12527cc1941";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
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
    doCheck = true;
  };

  py = self.buildPythonPackage {
    name = "py-1.4.30";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/py/py-1.4.30.tar.gz";
      md5 = "a904aabfe4765cb754f2db84ec7bb03a";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  
  pytest-capturelog = self.buildPythonPackage {
    name = "pytest-capturelog-0.7";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pytest-capturelog/pytest-capturelog-0.7.tar.gz";
      md5 = "cfeac23d8ed254deaeb50a8c0aa141e9";
    };
    propagatedBuildInputs = with self; [py];
    buildInputs = with self; [];
    doCheck = false;
  };

  redis-collections = self.buildPythonPackage {
    name = "redis-collections-0.1.7";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/r/redis-collections/redis-collections-0.1.7.tar.gz";
      md5 = "67aa817d9a2f1f63b3b3251062762e7d";
    };
    propagatedBuildInputs = with self; [redis];
    buildInputs = with self; [];
    doCheck = false;
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
      pkgs.graphviz
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

    build = [ setuptools-git ];
}
