{ buildPythonPackage
, fetchFromGitHub
}:

buildPythonPackage {
  name = "exif-1.0.10";
  src = fetchFromGitHub {
    repo = "exif-py";
    owner = "ianare";
    rev = "1.0.10";
    sha256 = "05i8ys2vgsykfm5h1c2j1vvla5zfb3kl6mxbsbqgannmdsf1p3bk";
  };
  prePatch = ''
    cp ${./setup.py} ./setup.py
  '';
  patches = [./0001-Diff-between-ianare-EXIF.py-and-lib-Exif-EXIF.py.patch];
}
