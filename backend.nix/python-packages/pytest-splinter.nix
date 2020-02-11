{ buildPythonPackage
, fetchurl
, setuptools
, splinter
, selenium
, pytest_2
, tox
}:

buildPythonPackage {
  name = "pytest-splinter-1.7.3";
  buildInputs = [ tox ];
  doCheck = true;
  propagatedBuildInputs = [ setuptools splinter selenium pytest_2 ];
  src = fetchurl {
    url = "https://pypi.python.org/packages/79/ad/c4c133028e4acd2dde93bb82ceca3a7498a19138116fa5067c8c79efd8e5/pytest-splinter-1.7.3.tar.gz";
    sha256 = "1sdbxgfgwfmc8nps8n4cc4rsjnvg40qrzv9iwcr8c5hn3q47by9q";
  };
}
