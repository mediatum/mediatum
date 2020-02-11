{ buildPythonPackage
, fetchurl
, prettytable
, ipython
, sqlalchemy
, sqlparse
, six
}:

buildPythonPackage {
  name = "ipython-sql-0.3.9";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/i/ipython-sql/ipython-sql-0.3.9.tar.gz";
    sha256 = "1vf3dhvdynd3wiwsw3a67fshy06r6d17qb1wns7rvf1q3wvzd1vi";
  };
  patchPhase = ''
    substituteInPlace setup.py --replace "import os" "import os;from codecs import open"
  '';
  propagatedBuildInputs = [prettytable ipython sqlalchemy sqlparse six];
}
