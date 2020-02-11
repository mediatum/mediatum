{ buildPythonPackage
, fetchurl
, six
}:

buildPythonPackage rec {
  name = "pymarc-${version}";
  version = "3.1.10";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/p/pymarc/pymarc-${version}.tar.gz";
    sha256 = "0yb91kcsk5bgljl55kimgwada9qr9w7ihl9j6ydbiakx8xqh47cf";
  };
  doCheck = false;
  propagatedBuildInputs = [ six ];
}
