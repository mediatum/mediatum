{ buildPythonPackage
, fetchFromGitHub
}:

buildPythonPackage {
  name = "pyexiftool-0.1";
  src = fetchFromGitHub {
    owner = "smarnach";
    repo = "pyexiftool";
    rev = "3db3764895e687d75b42d3ae4e554ca8664a7f6f";
    sha256 = "08wjxvkki668lkzw2da7z7sm2zwfy5d8zv6x1xrm8lcz3qbyf1cq";
  };
  doCheck = false;
}
