{ buildPythonPackage
, fetchurl
, wtforms
, flask
}:

buildPythonPackage {
  name = "flask-admin-1.5.2";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/F/Flask-Admin/Flask-Admin-1.5.2.tar.gz";
    sha256 = "0fsj91m7015svs8s0qzi8q8sf687g728d1ghykjh0rhzmzs3fabm";
  };
  propagatedBuildInputs = [ wtforms flask ];
  doCheck = false;
}
