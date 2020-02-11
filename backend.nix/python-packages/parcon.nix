{ buildPythonPackage
, fetchurl
}:

buildPythonPackage {
  name = "parcon-0.1.25";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/p/parcon/parcon-0.1.25.tar.gz";
    sha256 = "0kc7nf1ga5l901cbf7jydxm35kvzya4jq6syi2rlilsblaifpll2";
  };
}
