{ buildPythonPackage
, fetchurl
, six
, sqlalchemy
}:

buildPythonPackage {
  name = "SQLAlchemy-Utils-0.33.5";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/S/SQLAlchemy-Utils/SQLAlchemy-Utils-0.33.5.tar.gz";
    sha256 = "0z1n7r5h5j667lkgvps4dwwlf367786diilpq103252l1balcwnm";
  };
  doCheck = false;
  propagatedBuildInputs = [ six sqlalchemy ];
}
