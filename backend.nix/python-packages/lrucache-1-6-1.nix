{ buildPythonPackage
, fetchPypi
, setuptools_scm
}:

buildPythonPackage rec {
  pname = "backports.functools_lru_cache";
  version = "1.6.1";
  src = fetchPypi {
    inherit pname version;
    sha256 = "158ysf2hb0q4p4695abfiym9x1ywg0dgh8a3apd7gqaaxjy22jj4";
  };

  buildInputs = [ setuptools_scm ];
  doCheck = false;
}
