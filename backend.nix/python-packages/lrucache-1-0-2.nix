{ buildPythonPackage
, fetchPypi
, setuptools_scm
}:

let

  hgtools = buildPythonPackage rec {
    pname = "hgtools";
    version = "6.5.2";
    src = fetchPypi {
      inherit pname version;
      sha256 = "f9a31e2381b036d3fac3d7435d545ae4c7a27a93f8d722fdd65b8fef116d2b3c";
    };
    buildInputs = [ setuptools_scm ];
    doCheck = false;
  };

in

buildPythonPackage rec {
  pname = "backports.functools_lru_cache";
  version = "1.0.2";
  src = fetchPypi {
    inherit pname version;
    sha256 = "53fd3555b9135562f81a1c90ef87013fcd9422048b9a8662a7f9d41b2b44e29c";
  };

  buildInputs = [ hgtools ];
  doCheck = false;
}
