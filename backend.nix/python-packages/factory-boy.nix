{ buildPythonPackage
, fetchFromGitHub
, fake-factory
, mock
}:

buildPythonPackage {
  name = "factory-boy";
  src = fetchFromGitHub {
    repo = "factory_boy";
    owner = "dpausp";
    rev = "36b4cffa336845b6b0d30b2e040930af53eb732e";
    sha256 = "12yhp5nn20pypcnyc1y7gr08dsw3a5x7k2z3gm2z4jyhldgh0a3a";
  };
  propagatedBuildInputs = [ fake-factory ];
  buildInputs = [ mock ];
  doCheck = false;
}
