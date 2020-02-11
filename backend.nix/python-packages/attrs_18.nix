{ buildPythonPackage
, fetchurl
}:

buildPythonPackage {
  name = "attrs-18.2.0";
  src = fetchurl {
    url = "https://pypi.python.org/packages/0f/9e/26b1d194aab960063b266170e53c39f73ea0d0d3f5ce23313e0ec8ee9bdf/attrs-18.2.0.tar.gz";
    sha256 = "0s9ydh058wmmf5v391pym877x4ahxg45dw6a0w4c7s5wgpigdjqh";
  };
  doCheck = false;
}
