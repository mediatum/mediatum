{ buildPythonPackage
, fetchurl
, PyExecJS
}:

buildPythonPackage rec {
  name = "coffeescript-${version}";
  version = "2.0.3";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/C/CoffeeScript/CoffeeScript-${version}.tar.gz";
    sha256 = "02j8xsjw1sdqwm7myn8fl8c6ggil31yq0qfzwny5j96gmg3b5fr7";
  };
  propagatedBuildInputs = [ PyExecJS ];
  doCheck = false;
}
