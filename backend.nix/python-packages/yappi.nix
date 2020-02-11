{ buildPythonPackage
, fetchhg
}:

buildPythonPackage {
  name = "yappi-0.95";
  src = fetchhg {
    url = "https://bitbucket.org/sumerc/yappi/";
    rev = "69d70e0663fc";
    sha256 = "0phpkxwqill2g4vrh0fyn594jyck3l9r7fvik5906w6192z7k6yq";
  };
  doCheck = false;
}
