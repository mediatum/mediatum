{ buildPythonPackage
, fetchFromGitHub
, py
, pytest_2
}:

buildPythonPackage rec {
  name = "pytest-catchlog-${version}";
  version = "1.2.2";
  src = fetchFromGitHub {
    owner = "eisensheng";
    repo = "pytest-catchlog";
    rev = "e829f07d74b703397a07157fe919a8fd34014fa7";
    sha256 = "0c2r4gvj44yc2aqrfw5dr4y7ncf5qfkid1xj6gv1nc5xkzwzwfk1";
  };
  propagatedBuildInputs = [ py pytest_2 ];
}
