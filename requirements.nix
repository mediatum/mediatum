{ pkgs ? (import ./nixpkgs.nix {}).pkgs }:

let

  inherit (pkgs)
    fetchFromGitHub
    fetchgit
    fetchhg
    fetchpatch
    fetchurl
    stdenv
    file
    xorg
  ;

  inherit (import ./nixpkgs.nix {}) pkgs1803a;

  pythonPackages = pkgs.python2Packages;

  inherit (pythonPackages)
    Babel
    ConfigArgParse
    alabaster
    alembic
    bibtexparser
    buildPythonPackage
    decorator
    docutils
    flask
    flask_login
    httplib2
    humanize
    ipaddr
    ipdb
    ipykernel
    ipython
    jinja2
    ldap
    lxml
    mock
    munch
    pillow
    ply
    py
    pyPdf
    py_scrypt
    pyaml
    pygments
    pyjade
    pympler
    pyparsing
    python
    pyyaml
    reportlab
    requests
    setuptools
    setuptools-git
    six
    sqlalchemy
    sqlparse
    sympy
    tox
    unicodecsv
    werkzeug
  ;

in

let

  coffeescript = buildPythonPackage rec {
    name = "coffeescript-${version}";
    version = "2.0.3";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/C/CoffeeScript/CoffeeScript-${version}.tar.gz";
      sha256 = "02j8xsjw1sdqwm7myn8fl8c6ggil31yq0qfzwny5j96gmg3b5fr7";
    };
    propagatedBuildInputs = [ PyExecJS ];
    doCheck = false;
  };

  flask-admin = buildPythonPackage {
    name = "flask-admin-1.5.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/F/Flask-Admin/Flask-Admin-1.5.2.tar.gz";
      sha256 = "0fsj91m7015svs8s0qzi8q8sf687g728d1ghykjh0rhzmzs3fabm";
    };
    propagatedBuildInputs = [ wtforms flask ];
    doCheck = false;
  };

  ipython-sql = buildPythonPackage {
    name = "ipython-sql-0.3.9";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/i/ipython-sql/ipython-sql-0.3.9.tar.gz";
      sha256 = "1vf3dhvdynd3wiwsw3a67fshy06r6d17qb1wns7rvf1q3wvzd1vi";
    };
    patchPhase = ''
      substituteInPlace setup.py --replace "import os" "import os;from codecs import open"
    '';
    propagatedBuildInputs = [prettytable ipython sqlalchemy sqlparse six];
  };

  magic = buildPythonPackage rec {
    name = "${file.name}";

    src = file.src;

    patchPhase = ''
      substituteInPlace python/magic.py --replace "find_library('magic')" "'${file}/lib/libmagic.so'"
    '';

    buildInputs = [ python file ];

    preConfigure = "cd python";
    doCheck = false;
  };

  mediatumfsm = buildPythonPackage {
    name = "mediatumfsm-0.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/m/mediatumfsm/mediatumfsm-0.1.tar.gz";
      sha256 = "0pwqfm8r8m5nq85cp97mgsh34kgjll9z03qb2ql441x4mj963hpx";
    };
    doCheck = false;
    propagatedBuildInputs = [ pydot2 ];
    buildInputs = [ setuptools-git ];
  };

  mediatumtal = buildPythonPackage {
    name = "mediatumtal-0.3.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/m/mediatumtal/mediatumtal-0.3.2.tar.gz";
      sha256 = "07vixbpv0a7dv0y64nsyz4ff98s5jgin6isshai7ng1xbnj4xbxs";
    };
  };

  mollyZ3950 = buildPythonPackage {
    name = "mollyZ3950-2.04-molly1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/m/mollyZ3950/mollyZ3950-2.04-molly1.tar.gz";
      sha256 = "024afgrc6ij8rfvp9w82ry19yb9v88y7fclmza4ani7njj9imk2a";
    };
    propagatedBuildInputs = [ ply ];
  };

  parcon = buildPythonPackage {
    name = "parcon-0.1.25";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/parcon/parcon-0.1.25.tar.gz";
      sha256 = "0kc7nf1ga5l901cbf7jydxm35kvzya4jq6syi2rlilsblaifpll2";
    };
  };

  prettytable = buildPythonPackage {
    name = "prettytable-0.7.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/PrettyTable/prettytable-0.7.2.tar.bz2";
      sha256 = "0diwsicwmiq2cpzpxri7cyl5fmsvicafw6nfqf6p6p322dji2g45";
    };
  };

  pydot2 = buildPythonPackage {
    name = "pydot2-1.0.33";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pydot2/pydot2-1.0.33.tar.gz";
      sha256 = "16xwl6907nwlp2lgsb00lwxya8m33yw2ylmj5dz0fdy4l60ydh02";
    };
    propagatedBuildInputs = [ pyparsing setuptools ];
  };

  PyExecJS = buildPythonPackage {
    name = "PyExecJS-1.5.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/ba/8e/aedef81641c8dca6fd0fb7294de5bed9c45f3397d67fddf755c1042c2642/PyExecJS-1.5.1.tar.gz";
      sha256 = "0p2hkxv7mzxvbw6c0217r68shmw13zbhmp3vzy1q34bn143ivk1l";
    };
    propagatedBuildInputs = [ six ];
    doCheck = false;
  };

  pyexiftool = buildPythonPackage {
    name = "pyexiftool-0.1";

    src = fetchFromGitHub {
      owner = "smarnach";
      repo = "pyexiftool";
      rev = "3db3764895e687d75b42d3ae4e554ca8664a7f6f";
      sha256 = "08wjxvkki668lkzw2da7z7sm2zwfy5d8zv6x1xrm8lcz3qbyf1cq";
    };
    doCheck = false;
  };

  pymarc = buildPythonPackage rec {
    name = "pymarc-${version}";
    version = "3.1.10";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/pymarc/pymarc-${version}.tar.gz";
      sha256 = "0yb91kcsk5bgljl55kimgwada9qr9w7ihl9j6ydbiakx8xqh47cf";
    };
    doCheck = false;
    propagatedBuildInputs = [ six ];
  };

  python-logstash = buildPythonPackage {
    name = "python-logstash-0.4.6";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/p/python-logstash/python-logstash-0.4.6.tar.gz";
      sha256 = "13763yx0k655y0c8gxv7jj6cqp45zypx2fmnc56jnn9zz1fkx50h";
    };
  };

  sqlalchemy-utils = buildPythonPackage {
    name = "SQLAlchemy-Utils-0.33.5";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/S/SQLAlchemy-Utils/SQLAlchemy-Utils-0.33.5.tar.gz";
      sha256 = "0z1n7r5h5j667lkgvps4dwwlf367786diilpq103252l1balcwnm";
    };
    doCheck = false;
    propagatedBuildInputs = [ six sqlalchemy ];
  };

  sqlalchemy-continuum = buildPythonPackage {
    name = "SQLAlchemy-Continuum-1.3.6";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/S/SQLAlchemy-Continuum/SQLAlchemy-Continuum-1.3.6.tar.gz";
      sha256 = "0bf0mnrfyzphcnib7mg0fly59m55xhqlway19r5p73b717j5i4ln";
    };
    doCheck = false;
    propagatedBuildInputs = [ sqlalchemy sqlalchemy-utils ];
  };

  wtforms = buildPythonPackage {
    name = "wtforms-2.2.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/W/WTForms/WTForms-2.2.1.zip";
      sha256 = "0vyl26y9cg409cfyj8rhqxazsdnd0jipgjw06civhrd53yyi1pzz";
    };
    patches = [
      # old wtforms seems to be unable to cope with new SQLAlchemy
      (fetchpatch {
        url = "https://github.com/wtforms/wtforms/commit/6cc9e87b9d22baa37a0570ce901b094170270ab4.patch";
        sha256 = "089xlw25qlsb6kz6gzl8rwwj1gx8nkhn3jgp4f0b8f0m5da2klyi";
      })
    ];
  };

  attrs = buildPythonPackage {
    name = "attrs-18.2.0";
    src = fetchurl {
      url = "https://pypi.python.org/packages/0f/9e/26b1d194aab960063b266170e53c39f73ea0d0d3f5ce23313e0ec8ee9bdf/attrs-18.2.0.tar.gz";
      sha256 = "0s9ydh058wmmf5v391pym877x4ahxg45dw6a0w4c7s5wgpigdjqh";
    };
    doCheck = false;
  };

  ### test /devel deps

  fake-factory = buildPythonPackage {
    name = "fake-factory-0.5.3";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/f/fake-factory/fake-factory-0.5.3.tar.gz";
      sha256 = "1vhjvwyggyy3x0kl8maxb8ybrpp1sm8yn239rw43w1yi3a4hgxch";
    };
    doCheck = false;
  };

  factory-boy = buildPythonPackage {
    name = "factory-boy";
    src = fetchFromGitHub {
      repo = "factory_boy";
      owner = "dpausp";
      rev = "36b4cffa336845b6b0d30b2e040930af53eb732e";
      sha256 = "12yhp5nn20pypcnyc1y7gr08dsw3a5x7k2z3gm2z4jyhldgh0a3a";
    };
    propagatedBuildInputs = [ fake-factory ];
    buildInputs = [ mock ];
    doCheck = false;
  };

  fdfgen = buildPythonPackage {
    name = "fdfgen";
    src = fetchFromGitHub {
      repo = "fdfgen";
      owner = "ccnmtl";
      rev = "release-0.16.1";
      sha256 = "12blpw45s5x6d47c8gbr78na8lvpfw0g9q259is0v6rfnrq1s1yd";
    };
  };

  pytest = buildPythonPackage {
    name = "pytest-2.9.2";
    doCheck = false;
    propagatedBuildInputs = [ py ];
    src = fetchurl {
      url = "https://pypi.python.org/packages/f0/ee/6e2522c968339dca7d9abfd5e71312abeeb5ee902e09b4daf44f07b2f907/pytest-2.9.2.tar.gz";
      sha256 = "1n6igbc1b138wx1q5gca4pqw1j6nsyicfxds5n0b5989kaxqmh8j";
    };
  };

  pytest-catchlog = buildPythonPackage rec {
    name = "pytest-catchlog-${version}";
    version = "1.2.2";
    src = fetchFromGitHub {
      owner = "eisensheng";
      repo = "pytest-catchlog";
      rev = "e829f07d74b703397a07157fe919a8fd34014fa7";
      sha256 = "0c2r4gvj44yc2aqrfw5dr4y7ncf5qfkid1xj6gv1nc5xkzwzwfk1";
    };
    propagatedBuildInputs = [ py pytest ];
  };

  selenium = buildPythonPackage rec {
    name = "selenium-2.53.6";
    src = fetchurl {
      url = "https://pypi.python.org/packages/c9/d4/4c032f93dd8d198d51d06ce41005d02ae2e806d4e5b550255ddbeee4143b/selenium-2.53.6.tar.gz";
      sha256 = "05khnblqvgfjhni64yzhqzsqwxd5dr37lr6rinwp73bn2cgih1zm";
    };

    buildInputs = [ xorg.libX11 ];

    # Recompiling x_ignore_nofocus.so as the original one dlopen's libX11.so.6 by some
    # absolute paths. Replaced by relative path so it is found when used in nix.
    x_ignore_nofocus =
      fetchFromGitHub {
        owner = "SeleniumHQ";
        repo = "selenium";
        rev = "selenium-2.52.0";
        sha256 = "1n58akim9np2jy22jfgichq1ckvm8gglqi2hn3syphh0jjqq6cfx";
      };

    patchPhase = ''
      cp "${x_ignore_nofocus}/cpp/linux-specific/"* .
      substituteInPlace x_ignore_nofocus.c --replace "/usr/lib/libX11.so.6" "${xorg.libX11}/lib/libX11.so.6"
      gcc -c -fPIC x_ignore_nofocus.c -o x_ignore_nofocus.o
      gcc -shared \
        -Wl,${if stdenv.isDarwin then "-install_name" else "-soname"},x_ignore_nofocus.so \
        -o x_ignore_nofocus.so \
        x_ignore_nofocus.o
      cp -v x_ignore_nofocus.so py/selenium/webdriver/firefox/${if stdenv.is64bit then "amd64" else "x86"}/
    '';
  };

  splinter = buildPythonPackage {
    name = "splinter-0.7.3";
    doCheck = false;
    propagatedBuildInputs = [ selenium ];
    src = fetchurl {
      url = "https://pypi.python.org/packages/40/b9/7cac56d0f1f419b11ccf0ce9dcd924abe4b7dd17e2be1eb49862568550b4/splinter-0.7.3.tar.gz";
      sha256 = "1nxd02f5zqs51ks4ww6j3pr54g02m4q7bp2dysd4ms8vpkjkhp9y";
    };
  };

  pytest-splinter = buildPythonPackage {
    name = "pytest-splinter-1.7.3";
    buildInputs = [ tox ];
    doCheck = true;
    propagatedBuildInputs = [ setuptools splinter selenium pytest ];
    src = fetchurl {
      url = "https://pypi.python.org/packages/79/ad/c4c133028e4acd2dde93bb82ceca3a7498a19138116fa5067c8c79efd8e5/pytest-splinter-1.7.3.tar.gz";
      sha256 = "1sdbxgfgwfmc8nps8n4cc4rsjnvg40qrzv9iwcr8c5hn3q47by9q";
    };
  };

  pytest-base-url = buildPythonPackage {
    name = "pytest-base-url-1.1.0";
    doCheck = false;
    propagatedBuildInputs = [ pytest requests ];
    src = fetchurl {
      url = "https://pypi.python.org/packages/26/72/13d09fca6e5ad4ee263aaff01a662105646036135d8f8989b965f6a10274/pytest-base-url-1.1.0.tar.gz";
      sha256 = "136j01wifqpcihzc20fp5w6brv7d00iy7bmm2w8j6n5501mcx8ch";
    };
  };

  yappi = buildPythonPackage {
    name = "yappi-0.95";
    src = fetchhg {
      url = "https://bitbucket.org/sumerc/yappi/";
      rev = "69d70e0663fc";
      sha256 = "0phpkxwqill2g4vrh0fyn594jyck3l9r7fvik5906w6192z7k6yq";
    };
    doCheck = false;
  };

  sphinx = buildPythonPackage {
    name = "Sphinx-1.4.6";
    src = fetchurl {
      url = "https://pypi.python.org/packages/55/77/75d85633ae923006d6942cc16cf11ba2cbd6c3bd3cac5de029c46aa04afe/Sphinx-1.4.6.tar.gz";
      sha256 = "9e43430aa9b491ecd86302a1320edb8977da624f63422d494257eab2541a79d3";
    };
    doCheck = false;
    propagatedBuildInputs = [
      Babel
      jinja2
      pygments
      alabaster
      docutils
      six
      snowballstemmer
      imagesize
    ];
  };

  snowballstemmer = buildPythonPackage {
    name = "snowballstemmer-1.2.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/20/6b/d2a7cb176d4d664d94a6debf52cd8dbae1f7203c8e42426daa077051d59c/snowballstemmer-1.2.1.tar.gz";
      sha256 = "919f26a68b2c17a7634da993d91339e288964f93c274f1343e3bbbe2096e1128";
    };
    doCheck = false;
  };

  imagesize = buildPythonPackage {
    name = "imagesize-0.7.1";
    src = fetchurl {
      url = "https://pypi.python.org/packages/53/72/6c6f1e787d9cab2cc733cf042f125abec07209a58308831c9f292504e826/imagesize-0.7.1.tar.gz";
      sha256 = "0ab2c62b87987e3252f89d30b7cedbec12a01af9274af9ffa48108f2c13c6062";
    };
    doCheck = false;
  };

in

{

  production = [
    # python deps
    alembic
    attrs
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
    py_scrypt
    sqlalchemy
    sqlalchemy-continuum
    sqlalchemy-utils
    sympy
    unicodecsv
    werkzeug
    # other
    pkgs.ffmpeg
    pkgs1803a.ghostscript
    pkgs1803a.graphicsmagick
    pkgs.graphviz-nox
    pkgs.icu
    pkgs.pdftk
    pkgs.perlPackages.ImageExifTool
    pkgs.poppler_utils
    pkgs.glibcLocales
    (pkgs.callPackage ./uwsgi.nix {})
    (pkgs.callPackage ./postgresql.nix {})
    (pkgs.callPackage ./nginx.nix {})
  ];

  devel = [
    factory-boy
    ipykernel
    mock
    munch
    pytest
    pytest-catchlog
    pytest-base-url
    pytest-splinter
    sphinx
    yappi
  ];

  system = [
    pkgs.git
    pythonPackages.psycopg2
    pkgs.zsh
  ];

  build = [
    setuptools-git
  ];

}
