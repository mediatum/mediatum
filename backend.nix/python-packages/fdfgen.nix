{ buildPythonPackage
, fetchFromGitHub
}:

buildPythonPackage {
  name = "fdfgen";
  src = fetchFromGitHub {
    repo = "fdfgen";
    owner = "ccnmtl";
    rev = "release-0.16.1";
    sha256 = "12blpw45s5x6d47c8gbr78na8lvpfw0g9q259is0v6rfnrq1s1yd";
  };
}
