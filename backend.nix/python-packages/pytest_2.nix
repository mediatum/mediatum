{ buildPythonPackage
, fetchurl
, py
}:

buildPythonPackage {
  name = "pytest-2.9.2";
  doCheck = false;
  propagatedBuildInputs = [ py ];
  src = fetchurl {
    url = "https://pypi.python.org/packages/f0/ee/6e2522c968339dca7d9abfd5e71312abeeb5ee902e09b4daf44f07b2f907/pytest-2.9.2.tar.gz";
    sha256 = "1n6igbc1b138wx1q5gca4pqw1j6nsyicfxds5n0b5989kaxqmh8j";
  };
}
