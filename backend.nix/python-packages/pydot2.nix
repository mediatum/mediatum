{ buildPythonPackage
, fetchurl
, pyparsing
, setuptools
}:

buildPythonPackage {
  name = "pydot2-1.0.33";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/p/pydot2/pydot2-1.0.33.tar.gz";
    sha256 = "16xwl6907nwlp2lgsb00lwxya8m33yw2ylmj5dz0fdy4l60ydh02";
  };
  propagatedBuildInputs = [ pyparsing setuptools ];
}
