{ buildPythonPackage
, fetchurl
, sqlalchemy
, sqlalchemy-utils
}:

buildPythonPackage {
  name = "SQLAlchemy-Continuum-1.3.9";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/S/SQLAlchemy-Continuum/SQLAlchemy-Continuum-1.3.9.tar.gz";
    sha256 = "0b7q0rqy5q7m9yw7yl7jzrk8p1jh1hqmqvzf45rwmwxs724kfkjg";
  };
  doCheck = false;
  propagatedBuildInputs = [ sqlalchemy sqlalchemy-utils ];
}
