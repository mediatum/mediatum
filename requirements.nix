{fetchurl, fetchgit, stdenv, self, pkgs}:

let
  self = pkgs.pythonPackages;

  pyaml = self.buildPythonPackage {
    name = "pyaml-15.6.3";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/36a/769535f45c2d0/pyaml-15.6.3.tar.gz";
      md5 = "36a769535f45c2d04feb9ba50cfbbd3d";
    };
    propagatedBuildInputs = with self; [pyyaml];
    buildInputs = with self; [];
    doCheck = false;
  };
  pydot2 = self.buildPythonPackage {
    name = "pydot2-1.0.33";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/33d/dc024f5f3df45/pydot2-1.0.33.tar.gz";
      md5 = "33ddc024f5f3df4522ab2d867bdedb0d";
    };
    propagatedBuildInputs = with self; [pyparsing setuptools];
    buildInputs = with self; [];
    doCheck = false;
  };
  python-Levenshtein = self.buildPythonPackage {
    name = "python-Levenshtein-0.12.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/e8c/de197d6d304bb/python-Levenshtein-0.12.0.tar.gz";
      md5 = "e8cde197d6d304bbdc3adae66fec99fb";
    };
    propagatedBuildInputs = with self; [setuptools];
    buildInputs = with self; [];
    doCheck = false;
  };
  scrypt = self.buildPythonPackage {
    name = "scrypt-0.7.1";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/9fe/b713f183e11ca/scrypt-0.7.1.tar.gz";
      md5 = "9feb713f183e11caa940e8ec71cf1361";
    };
    propagatedBuildInputs = with self; [pkgs.openssl];
    buildInputs = with self; [];
    doCheck = false;
  };
  pip = self.buildPythonPackage {
    name = "pip-7.1.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/d93/5ee9146074b1d/pip-7.1.0.tar.gz";
      md5 = "d935ee9146074b1d3f26c5f0acfd120e";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  pyparsing = self.buildPythonPackage {
    name = "pyparsing-2.0.3";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/0a5/ec41bb650aed8/pyparsing-2.0.3.zip";
      md5 = "0a5ec41bb650aed802751a311b5d820d";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  mediatumbabel = self.buildPythonPackage {
    name = "mediatumbabel-0.1.1";
    src = fetchurl {
      url = "http://localhost:3141/stenzel/dev/+f/125/a2daa5936d0b3/mediatumbabel-0.1.1.tar.gz";
      md5 = "125a2daa5936d0b3d2e213dc33e0bab5";
    };
    propagatedBuildInputs = with self; [babel];
    buildInputs = with self; [setuptools-git];
    doCheck = false;
  };
  reportlab = self.buildPythonPackage {
    name = "reportlab-3.2.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/79d/059e797c557ae/reportlab-3.2.0.tar.gz";
      md5 = "79d059e797c557aed4b40c68dd6c7eae";
    };
    propagatedBuildInputs = with self; [pillow pip setuptools];
    buildInputs = with self; [pkgs.freetype pkgs.gnome.libart_lgpl];
    doCheck = false;
  };
  parcon = self.buildPythonPackage {
    name = "parcon-0.1.25";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/146/ab4d138fd5b18/parcon-0.1.25.tar.gz";
      md5 = "146ab4d138fd5b1848390fbf199c3ac2";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  sqlalchemy-utils = self.buildPythonPackage {
    name = "sqlalchemy-utils-0.30.15";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/719/ac730d44e25ff/SQLAlchemy-Utils-0.30.15.tar.gz";
      md5 = "719ac730d44e25ff641f2cc8e2a1597d";
    };
    propagatedBuildInputs = with self; [six sqlalchemy];
    buildInputs = with self; [];
    doCheck = false;
  };

  psycopg2 = self.buildPythonPackage {
    name = "psycopg2-2.6.1";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/842/b44f8c95517ed/psycopg2-2.6.1.tar.gz";
      md5 = "842b44f8c95517ed5b792081a2370da1";
    };
    propagatedBuildInputs = with self; [pkgs.postgresql94];
    buildInputs = with self; [];
    doCheck = false;
  };
  six = self.buildPythonPackage {
    name = "six-1.9.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/476/881ef4012262d/six-1.9.0.tar.gz";
      md5 = "476881ef4012262dfc8adc645ee786c4";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  ipaddr = self.buildPythonPackage {
    name = "ipaddr-2.1.11";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/f2c/7852f95862715/ipaddr-2.1.11.tar.gz";
      md5 = "f2c7852f95862715f92e7d089dc3f2cf";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  coffeescript = self.buildPythonPackage {
    name = "coffeescript-1.1.1";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/696/03dbdaf65e0f6/CoffeeScript-1.1.1.zip";
      md5 = "69603dbdaf65e0f6bd682b946ea5bd2d";
    };
    propagatedBuildInputs = with self; [PyExecJS];
    buildInputs = with self; [];
    doCheck = false;
  };

  setuptools-git = self.buildPythonPackage {
    name = "setuptools-git-1.1";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/7b5/967e9527c789c/setuptools-git-1.1.tar.gz";
      md5 = "7b5967e9527c789c3113b07a1f196f6e";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  werkzeug = self.buildPythonPackage {
    name = "werkzeug-0.10.4";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/66a/488e0ac50a9ec/Werkzeug-0.10.4.tar.gz";
      md5 = "66a488e0ac50a9ec326fe020b3083450";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  sympy = self.buildPythonPackage {
    name = "sympy-0.7.6";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/3d0/4753974306d8a/sympy-0.7.6.tar.gz";
      md5 = "3d04753974306d8a13830008e17babca";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  mediatumfsm = self.buildPythonPackage {
    name = "mediatumfsm-0.1dev";
    src = fetchurl {
      url = "http://localhost:3141/stenzel/dev/+f/24a/ef8e9879485a1/mediatumfsm-0.1dev.tar.gz";
      md5 = "24aef8e9879485a19d4c07a335ad8f3a";
    };
    propagatedBuildInputs = with self; [pydot2];
    buildInputs = with self; [setuptools-git];
    doCheck = false;
  };
  mediatumtal = self.buildPythonPackage {
    name = "mediatumtal-0.2";
    src = fetchurl {
      url = "http://localhost:3141/stenzel/dev/+f/941/7c004088510e2/mediatumtal-0.2.tar.gz";
      md5 = "9417c004088510e25e6dd2e4ebd54ee0";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

  sqlalchemy = self.buildPythonPackage {
    name = "sqlalchemy-1.0.8";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/7cf/d005be63945c9/SQLAlchemy-1.0.8.tar.gz";
      md5 = "7cfd005be63945c96a78c67764ac3a85";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  PyExecJS = self.buildPythonPackage {
    name = "PyExecJS-1.1.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/027/bcbc0a2f44419/PyExecJS-1.1.0.zip";
      md5 = "027bcbc0a2f44419a6be1e3c4d5d68a1";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  MarkupSafe = self.buildPythonPackage {
    name = "MarkupSafe-0.23";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/f5a/b3deee4c37cd6/MarkupSafe-0.23.tar.gz";
      md5 = "f5ab3deee4c37cd6a922fb81e730da6e";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  pytz = self.buildPythonPackage {
    name = "pytz-2015.4";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/233/f2a2b370d03f9/pytz-2015.4.zip";
      md5 = "233f2a2b370d03f9b5911700cc9ebf3c";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  jinja2 = self.buildPythonPackage {
    name = "jinja2-2.8";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/edb/51693fe22c53c/Jinja2-2.8.tar.gz";
      md5 = "edb51693fe22c53cee5403775c71a99e";
    };
    propagatedBuildInputs = with self; [MarkupSafe];
    buildInputs = with self; [];
    doCheck = false;
  };
  httplib2 = self.buildPythonPackage {
    name = "httplib2-0.9.1";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/5db/0cec10d9bf6bd/httplib2-0.9.1.zip";
      md5 = "5db0cec10d9bf6bd6767820ac304a3ce";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  python-logstash = self.buildPythonPackage {
    name = "python-logstash-0.4.5";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/401/462a61563f992/python-logstash-0.4.5.tar.gz";
      md5 = "401462a61563f992894bd65c976e556b";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  decorator = self.buildPythonPackage {
    name = "decorator-4.0.2";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/033/c9563af492c4c/decorator-4.0.2.tar.gz";
      md5 = "033c9563af492c4ce2680ee6ca481fa7";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  pyyaml = self.buildPythonPackage {
    name = "pyyaml-3.11";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/89c/bc92cda979042/PyYAML-3.11.zip";
      md5 = "89cbc92cda979042533b640b76e6e055";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  pydot = self.buildPythonPackage {
    name = "pydot-1.0.28";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+e/http_pydot.googlecode.com_files/pydot-1.0.28.tar.gz";
      sha256 = "1pyrdva1qmb5chh1d2yzzhg5zldjw3yxl643m42z7f2g21xzzshy";
    };
    propagatedBuildInputs = with self; [pyparsing setuptools];
    buildInputs = with self; [];
    doCheck = false;
  };
  pypdf = self.buildPythonPackage {
    name = "pypdf-1.13";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+e/http_pybrary.net_pyPdf/pyPdf-1.13.zip";
      sha256 = "1w277d9zxf6l6p817d8i4c1kknsyqj4pbbafjy32l7i8dhxwdkqv";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  pymarc = self.buildPythonPackage {
    name = "pymarc-3.0.4";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/8d6/fe58482054276/pymarc-3.0.4.tar.gz";
      md5 = "8d6fe584820542760b2f954076fba9aa";
    };
    propagatedBuildInputs = with self; [six];
    buildInputs = with self; [];
    doCheck = false;
  };
  unicodecsv = self.buildPythonPackage {
    name = "unicodecsv-0.13.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/e22/3b525abd372b5/unicodecsv-0.13.0.tar.gz";
      md5 = "e223b525abd372b559e3277278418985";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  setuptools = self.buildPythonPackage {
    name = "setuptools-18.0.1";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/974/6c2a5347128d0/setuptools-18.0.1.zip";
      md5 = "9746c2a5347128d00189e3900e88cc52";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  babel = self.buildPythonPackage {
    name = "babel-2.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/629/17719897a81e2/Babel-2.0.tar.gz";
      md5 = "62917719897a81e22dcaa3b17eeb11d8";
    };
    propagatedBuildInputs = with self; [pytz];
    buildInputs = with self; [];
    doCheck = false;
  };
  requests = self.buildPythonPackage {
    name = "requests-2.7.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/29b/173fd5fa572ec/requests-2.7.0.tar.gz";
      md5 = "29b173fd5fa572ec0764d1fd7b527260";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  pillow = self.buildPythonPackage {
    name = "pillow-2.9.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/cd4/e6286fb28e277/Pillow-2.9.0.zip";
      md5 = "cd4e6286fb28e277954c011c3ce05bc4";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [pkgs.zlib pkgs.libjpeg pkgs.libtiff pkgs.freetype pkgs.lcms2 pkgs.libwebp];
    doCheck = false;
  };
  pyjade = self.buildPythonPackage {
    name = "pyjade-3.1.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/e6a/38f7c5c4f6fde/pyjade-3.1.0.tar.gz";
      md5 = "e6a38f7c5c4f6fdee15800592a85eb1d";
    };
    propagatedBuildInputs = with self; [six];
    buildInputs = with self; [];
    doCheck = false;
  };

  lxml = self.buildPythonPackage {
    name = "lxml-3.4.4";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/a9a/65972afc173ec/lxml-3.4.4.tar.gz";
      md5 = "a9a65972afc173ec7a39c585f4eea69c";
    };
    propagatedBuildInputs = with self; [pkgs.libxml2 pkgs.libxslt];
    buildInputs = with self; [];
    doCheck = false;
  };

  pytest-capturelog = self.buildPythonPackage {
    name = "pytest-capturelog-0.7";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/cfe/ac23d8ed254de/pytest-capturelog-0.7.tar.gz";
      md5 = "cfeac23d8ed254deaeb50a8c0aa141e9";
    };
    propagatedBuildInputs = with self; [py];
    buildInputs = with self; [];
    doCheck = false;
  };
  py = self.buildPythonPackage {
    name = "py-1.4.30";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/a90/4aabfe4765cb7/py-1.4.30.tar.gz";
      md5 = "a904aabfe4765cb754f2db84ec7bb03a";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  munch = self.buildPythonPackage {
    name = "munch-2.0.2";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/6bf/f44f4f33b0af4/munch-2.0.2.tar.gz";
      md5 = "6bff44f4f33b0af4f6f991a996f5a314";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  fake-factory = self.buildPythonPackage {
    name = "fake-factory-0.5.2";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/c32/835b3fed1f18b/fake-factory-0.5.2.tar.gz";
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
      url = "http://localhost:3141/root/pypi/+f/dcd/8e891474d605b/pytest-2.7.2.tar.gz";
      md5 = "dcd8e891474d605b81fc7fcc8711e95b";
    };
    propagatedBuildInputs = with self; [py];
    buildInputs = with self; [];
    doCheck = false;
  };

  ipython = self.buildPythonPackage {
    name = "ipython-3.2.1";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/5b0/84f3281d5f8f0/ipython-3.2.1.zip";
      md5 = "5b084f3281d5f8f098d13fac99fdc847";
    };
    propagatedBuildInputs = with self; [readline python.modules.sqlite3];
    buildInputs = with self; [];
    doCheck = false;
  };

  funcsigs = self.buildPythonPackage {
    name = "funcsigs-0.4";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/fb1/d031f284233e0/funcsigs-0.4.tar.gz";
      md5 = "fb1d031f284233e09701f6db1281c2a5";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };
  mock = self.buildPythonPackage {
    name = "mock-1.1.2";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/4f3/f256655ab8f39/mock-1.1.2.tar.gz";
      md5 = "4f3f256655ab8f39a1d364ab868e1677";
    };
    propagatedBuildInputs = with self; [pbr six funcsigs];
    buildInputs = with self; [];
    doCheck = false;
  };
  pbr = self.buildPythonPackage {
    name = "pbr-1.3.0";
    src = fetchurl {
      url = "http://localhost:3141/root/pypi/+f/5e5/4c9e7f083b525/pbr-1.3.0.tar.gz";
      md5 = "5e54c9e7f083b5259a6e619dfd6525f8";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

in {
  production = [
      parcon
      sqlalchemy
      sqlalchemy-utils
      psycopg2
      python-Levenshtein
      pymarc
      requests
      pydot
      reportlab
      pyaml
      pyyaml
      jinja2
      werkzeug
      pyjade
      coffeescript
      lxml
      python-logstash
      scrypt
      ipaddr
      decorator
      pypdf
      sympy
      unicodecsv
      httplib2
      mediatumbabel
      mediatumtal
      mediatumfsm
      mock
      pkgs.pythonPackages.ldap
    ];

    devel = [
      pytest
      factory-boy
      munch
      pytest-capturelog
      ipython
    ];

    system = with pkgs; [
      zsh
      git
      ffmpeg
      nginx
      graphviz
      imagemagick
    ];

}
