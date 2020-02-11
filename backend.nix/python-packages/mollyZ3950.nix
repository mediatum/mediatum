{ buildPythonPackage
, fetchurl
, ply
}:

buildPythonPackage {
  name = "mollyZ3950-2.04-molly1";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/m/mollyZ3950/mollyZ3950-2.04-molly1.tar.gz";
    sha256 = "024afgrc6ij8rfvp9w82ry19yb9v88y7fclmza4ani7njj9imk2a";
  };
  propagatedBuildInputs = [ ply ];
}
