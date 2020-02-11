{ buildPythonPackage
, fetchurl
, Babel
, jinja2
, pygments
, alabaster
, docutils
, six
, snowballstemmer_without_PyStemmer
, imagesize_0_7_1
}:

buildPythonPackage {
  name = "Sphinx-1.4.6";
  src = fetchurl {
    url = "https://pypi.python.org/packages/55/77/75d85633ae923006d6942cc16cf11ba2cbd6c3bd3cac5de029c46aa04afe/Sphinx-1.4.6.tar.gz";
    sha256 = "9e43430aa9b491ecd86302a1320edb8977da624f63422d494257eab2541a79d3";
  };
  doCheck = false;
  propagatedBuildInputs = [
    Babel
    jinja2
    pygments
    alabaster
    docutils
    six
    snowballstemmer_without_PyStemmer
    imagesize_0_7_1
  ];
}
