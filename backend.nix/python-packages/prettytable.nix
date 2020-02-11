{ buildPythonPackage
, fetchurl
}:

buildPythonPackage {
  name = "prettytable-0.7.2";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/P/PrettyTable/prettytable-0.7.2.tar.bz2";
    sha256 = "0diwsicwmiq2cpzpxri7cyl5fmsvicafw6nfqf6p6p322dji2g45";
  };
}
