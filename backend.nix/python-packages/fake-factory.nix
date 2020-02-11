{ buildPythonPackage
, fetchurl
}:

buildPythonPackage {
  name = "fake-factory-0.5.3";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/f/fake-factory/fake-factory-0.5.3.tar.gz";
    sha256 = "1vhjvwyggyy3x0kl8maxb8ybrpp1sm8yn239rw43w1yi3a4hgxch";
  };
  doCheck = false;
}
