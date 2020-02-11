{ buildPythonPackage
, fetchurl
, pydot2
, setuptools-git
}:

buildPythonPackage {
  name = "mediatumfsm-0.1";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/m/mediatumfsm/mediatumfsm-0.1.tar.gz";
    sha256 = "0pwqfm8r8m5nq85cp97mgsh34kgjll9z03qb2ql441x4mj963hpx";
  };
  doCheck = false;
  propagatedBuildInputs = [ pydot2 ];
  buildInputs = [ setuptools-git ];
}
