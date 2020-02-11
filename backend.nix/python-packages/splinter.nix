{ buildPythonPackage
, fetchurl
, selenium
}:

buildPythonPackage {
  name = "splinter-0.7.3";
  doCheck = false;
  propagatedBuildInputs = [ selenium ];
  src = fetchurl {
    url = "https://pypi.python.org/packages/40/b9/7cac56d0f1f419b11ccf0ce9dcd924abe4b7dd17e2be1eb49862568550b4/splinter-0.7.3.tar.gz";
    sha256 = "1nxd02f5zqs51ks4ww6j3pr54g02m4q7bp2dysd4ms8vpkjkhp9y";
  };
}
