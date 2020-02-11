{ buildPythonPackage
, fetchurl
, sqlalchemy
, sqlalchemy-utils
}:

buildPythonPackage {
  name = "SQLAlchemy-Continuum-1.3.6";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/S/SQLAlchemy-Continuum/SQLAlchemy-Continuum-1.3.6.tar.gz";
    sha256 = "0bf0mnrfyzphcnib7mg0fly59m55xhqlway19r5p73b717j5i4ln";
  };
  doCheck = false;
  propagatedBuildInputs = [ sqlalchemy sqlalchemy-utils ];
}
