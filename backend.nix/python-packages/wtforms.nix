{ buildPythonPackage
, fetchurl
, fetchpatch
}:

buildPythonPackage {
  name = "wtforms-2.2.1";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/W/WTForms/WTForms-2.2.1.zip";
    sha256 = "0vyl26y9cg409cfyj8rhqxazsdnd0jipgjw06civhrd53yyi1pzz";
  };
  patches = [
    # old wtforms seems to be unable to cope with new SQLAlchemy
    (fetchpatch {
      url = "https://github.com/wtforms/wtforms/commit/6cc9e87b9d22baa37a0570ce901b094170270ab4.patch";
      sha256 = "089xlw25qlsb6kz6gzl8rwwj1gx8nkhn3jgp4f0b8f0m5da2klyi";
   })
  ];
}
