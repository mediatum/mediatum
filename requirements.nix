{fetchurl, fetchgit, stdenv, self, pkgs}:

let
  self = pkgs.pythonPackages;

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
  pip = self.buildPythonPackage {
    name = "pip-7.1.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pip/pip-7.1.0.tar.gz";
      md5 = "d935ee9146074b1d3f26c5f0acfd120e";
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
  mediatumbabel = self.buildPythonPackage {
    name = "mediatumbabel-0.1.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/m/mediatumbabel/mediatumbabel-0.1.1.tar.gz";
      md5 = "1d3cf44fc51b0a194853375f32968901";
    };
    propagatedBuildInputs = with self; [babel];
    buildInputs = with self; [setuptools-git];
    doCheck = false;
  };
  reportlab = self.buildPythonPackage {
    name = "reportlab-3.2.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/r/reportlab/reportlab-3.2.0.tar.gz";
      md5 = "79d059e797c557aed4b40c68dd6c7eae";
    };
    propagatedBuildInputs = with self; [pillow pip setuptools];
    buildInputs = with self; [pkgs.freetype pkgs.gnome.libart_lgpl];
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

  sqlalchemy-utils = self.buildPythonPackage {
    name = "sqlalchemy-utils-0.30.15";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/S/SQLAlchemy-Utils/SQLAlchemy-Utils-0.30.15.tar.gz";
      md5 = "719ac730d44e25ff641f2cc8e2a1597d";
    };
    propagatedBuildInputs = with self; [six sqlalchemy];
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
  six = self.buildPythonPackage {
    name = "six-1.9.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/s/six/six-1.9.0.tar.gz";
      md5 = "476881ef4012262dfc8adc645ee786c4";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
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

  setuptools-git = self.buildPythonPackage {
    name = "setuptools-git-1.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/s/setuptools-git/setuptools-git-1.1.tar.gz";
      md5 = "7b5967e9527c789c3113b07a1f196f6e";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  werkzeug = self.buildPythonPackage {
    name = "werkzeug-0.10.4";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/W/Werkzeug/Werkzeug-0.10.4.tar.gz";
      md5 = "66a488e0ac50a9ec326fe020b3083450";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  sympy = self.buildPythonPackage {
    name = "sympy-0.7.6";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/s/sympy/sympy-0.7.6.tar.gz";
      md5 = "3d04753974306d8a13830008e17babca";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
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
    name = "mediatumtal-0.2";
    src = fetchurl {
      url = https://pypi.python.org/packages/source/m/mediatumtal/mediatumtal-0.2.tar.gz;
      md5 = "f1d01862e6d93e85174a1c85e7ef8c6e";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  sqlalchemy = self.buildPythonPackage {
    name = "sqlalchemy-1.0.8";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/S/SQLAlchemy/SQLAlchemy-1.0.8.tar.gz";
      md5 = "7cfd005be63945c96a78c67764ac3a85";
    };
    propagatedBuildInputs = with self; [];
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
  MarkupSafe = self.buildPythonPackage {
    name = "MarkupSafe-0.23";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/M/MarkupSafe/MarkupSafe-0.23.tar.gz";
      md5 = "f5ab3deee4c37cd6a922fb81e730da6e";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  pytz = self.buildPythonPackage {
    name = "pytz-2015.4";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pytz/pytz-2015.4.zip";
      md5 = "233f2a2b370d03f9b5911700cc9ebf3c";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  jinja2 = self.buildPythonPackage {
    name = "jinja2-2.8";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/J/Jinja2/Jinja2-2.8.tar.gz";
      md5 = "edb51693fe22c53cee5403775c71a99e";
    };
    propagatedBuildInputs = with self; [MarkupSafe];
    buildInputs = with self; [];
    doCheck = false;
  };
  httplib2 = self.buildPythonPackage {
    name = "httplib2-0.9.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/h/httplib2/httplib2-0.9.1.zip";
      md5 = "5db0cec10d9bf6bd6767820ac304a3ce";
    };
    propagatedBuildInputs = with self; [];
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
  decorator = self.buildPythonPackage {
    name = "decorator-4.0.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/d/decorator/decorator-4.0.2.tar.gz";
      md5 = "033c9563af492c4ce2680ee6ca481fa7";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  pyyaml = self.buildPythonPackage {
    name = "pyyaml-3.11";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/PyYAML/PyYAML-3.11.zip";
      md5 = "89cbc92cda979042533b640b76e6e055";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  pydot = self.buildPythonPackage {
    name = "pydot-1.0.28";
    src = fetchurl {
      url = "http://pydot.googlecode.com/files/pydot-1.0.28.tar.gz";
      sha256 = "1pyrdva1qmb5chh1d2yzzhg5zldjw3yxl643m42z7f2g21xzzshy";
    };
    propagatedBuildInputs = with self; [pyparsing setuptools];
    buildInputs = with self; [];
    doCheck = false;
  };
  pypdf = self.buildPythonPackage {
    name = "pypdf-1.13";
    src = fetchurl {
      url = https://pypi.python.org/packages/source/p/pyPdf/pyPdf-1.13.tar.gz;
      md5= "7a75ef56f227b78ae62d6e38d4b6b1da";
    };
    propagatedBuildInputs = with self; [];
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
  unicodecsv = self.buildPythonPackage {
    name = "unicodecsv-0.13.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/u/unicodecsv/unicodecsv-0.13.0.tar.gz";
      md5 = "e223b525abd372b559e3277278418985";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  setuptools = self.buildPythonPackage {
    name = "setuptools-18.0.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/s/setuptools/setuptools-18.0.1.zip";
      md5 = "9746c2a5347128d00189e3900e88cc52";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  babel = self.buildPythonPackage {
    name = "babel-2.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/B/Babel/Babel-2.0.tar.gz";
      md5 = "62917719897a81e22dcaa3b17eeb11d8";
    };
    propagatedBuildInputs = with self; [pytz];
    buildInputs = with self; [];
    doCheck = false;
  };
  requests = self.buildPythonPackage {
    name = "requests-2.7.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/r/requests/requests-2.7.0.tar.gz";
      md5 = "29b173fd5fa572ec0764d1fd7b527260";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  pillow = self.buildPythonPackage {
    name = "pillow-2.9.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/Pillow/Pillow-2.9.0.zip";
      md5 = "cd4e6286fb28e277954c011c3ce05bc4";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [pkgs.zlib pkgs.libjpeg pkgs.libtiff pkgs.freetype pkgs.lcms2 pkgs.libwebp];
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

  lxml = self.buildPythonPackage {
    name = "lxml-3.4.4";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/l/lxml/lxml-3.4.4.tar.gz";
      md5 = "a9a65972afc173ec7a39c585f4eea69c";
    };
    propagatedBuildInputs = with self; [pkgs.libxml2 pkgs.libxslt];
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
  munch = self.buildPythonPackage {
    name = "munch-2.0.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/m/munch/munch-2.0.2.tar.gz";
      md5 = "6bff44f4f33b0af4f6f991a996f5a314";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
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
  pytest = self.buildPythonPackage {
    name = "pytest-2.7.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pytest/pytest-2.7.2.tar.gz";
      md5 = "dcd8e891474d605b81fc7fcc8711e95b";
    };
    propagatedBuildInputs = with self; [py];
    buildInputs = with self; [];
    doCheck = false;
  };

  ipython = self.buildPythonPackage {
    name = "ipython-3.2.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/i/ipython/ipython-3.2.1.zip";
      md5 = "5b084f3281d5f8f098d13fac99fdc847";
    };
    propagatedBuildInputs = with self; [readline python.modules.sqlite3];
    buildInputs = with self; [];
    doCheck = false;
  };

  funcsigs = self.buildPythonPackage {
    name = "funcsigs-0.4";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/f/funcsigs/funcsigs-0.4.tar.gz";
      md5 = "fb1d031f284233e09701f6db1281c2a5";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  mock = self.buildPythonPackage {
    name = "mock-1.1.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/m/mock/mock-1.1.2.tar.gz";
      md5 = "4f3f256655ab8f39a1d364ab868e1677";
    };
    propagatedBuildInputs = with self; [pbr six funcsigs];
    buildInputs = with self; [];
    doCheck = false;
  };
  pbr = self.buildPythonPackage {
    name = "pbr-1.3.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pbr/pbr-1.3.0.tar.gz";
      md5 = "5e54c9e7f083b5259a6e619dfd6525f8";
    };
    propagatedBuildInputs = with self; [];
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

  sqlparse = self.buildPythonPackage {
    name = "sqlparse-0.1.16";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/s/sqlparse/sqlparse-0.1.16.tar.gz";
      md5 = "370962a307ebaaa70a28b6b0ccb53980";
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

  pygments = self.buildPythonPackage {
    name = "pygments-2.0.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/Pygments/Pygments-2.0.2.tar.gz";
      md5 = "238587a1370d62405edabd0794b3ec4a";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };


in {
  production = [
      coffeescript
      configargparse
      decorator
      httplib2
      ipaddr
      ipython
      ipython-sql
      jinja2
      lxml
      mediatumbabel
      mediatumfsm
      mediatumtal
      mock
      parcon
      pkgs.pythonPackages.ldap
      psycopg2
      pyaml
      pydot
      pygments
      pyjade
      pymarc
      pypdf
      python-Levenshtein
      python-logstash
      pyyaml
      reportlab
      requests
      scrypt
      sqlalchemy
      sqlalchemy-utils
      sympy
      unicodecsv
      werkzeug
    ];

    devel = [
      factory-boy
      munch
      pytest
      pytest-capturelog
    ];

    system = with pkgs; [
      ffmpeg
      git
      graphviz
      imagemagick
      nginx
      zsh
    ];

}
