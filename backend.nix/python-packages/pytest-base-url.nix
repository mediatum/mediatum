{ buildPythonPackage
, fetchurl
, pytest_2
, requests
}:

buildPythonPackage {
  name = "pytest-base-url-1.1.0";
  doCheck = false;
  propagatedBuildInputs = [ pytest_2 requests ];
  src = fetchurl {
    url = "https://pypi.python.org/packages/26/72/13d09fca6e5ad4ee263aaff01a662105646036135d8f8989b965f6a10274/pytest-base-url-1.1.0.tar.gz";
    sha256 = "136j01wifqpcihzc20fp5w6brv7d00iy7bmm2w8j6n5501mcx8ch";
  };
}
