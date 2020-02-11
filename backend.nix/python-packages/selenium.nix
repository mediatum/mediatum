{ buildPythonPackage
, fetchurl
, fetchFromGitHub
, xorg
, stdenv
}:

buildPythonPackage rec {
  name = "selenium-2.53.6";
  src = fetchurl {
    url = "https://pypi.python.org/packages/c9/d4/4c032f93dd8d198d51d06ce41005d02ae2e806d4e5b550255ddbeee4143b/selenium-2.53.6.tar.gz";
    sha256 = "05khnblqvgfjhni64yzhqzsqwxd5dr37lr6rinwp73bn2cgih1zm";
  };
  buildInputs = [ xorg.libX11 ];
  # Recompiling x_ignore_nofocus.so as the original one dlopen's libX11.so.6 by some
  # absolute paths. Replaced by relative path so it is found when used in nix.
  x_ignore_nofocus =
    fetchFromGitHub {
      owner = "SeleniumHQ";
      repo = "selenium";
      rev = "selenium-2.52.0";
      sha256 = "1n58akim9np2jy22jfgichq1ckvm8gglqi2hn3syphh0jjqq6cfx";
   };
  patchPhase = ''
    cp "${x_ignore_nofocus}/cpp/linux-specific/"* .
    substituteInPlace x_ignore_nofocus.c --replace "/usr/lib/libX11.so.6" "${xorg.libX11}/lib/libX11.so.6"
    gcc -c -fPIC x_ignore_nofocus.c -o x_ignore_nofocus.o
    gcc -shared \
      -Wl,${if stdenv.isDarwin then "-install_name" else "-soname"},x_ignore_nofocus.so \
      -o x_ignore_nofocus.so \
      x_ignore_nofocus.o
    cp -v x_ignore_nofocus.so py/selenium/webdriver/firefox/${if stdenv.is64bit then "amd64" else "x86"}/
  '';
}
