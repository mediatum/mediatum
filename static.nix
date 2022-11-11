{ pkgs ? (import ./nixpkgs.nix {}).pkgs
, lib ? pkgs.lib
, fetchurl ? pkgs.fetchurl
, fetchzip ? pkgs.fetchzip
, runCommand ? pkgs.runCommand
}:

let

  paths = {
    "css/jquery-ui-1.12.1.css" = "../jquery-ui-1.12.1/jquery-ui.css";
    "fancytree" = fetchzip {
      url = "https://github.com/mar10/fancytree/archive/refs/tags/v2.4.1.tar.gz";
      hash = "sha512-O3AP9eu6ONtsCI1BOp2JlhiEpFKOzejeZLQ2KoChd9BKXan7CWsgkfGbuDRiE/wD3QWwEGv+Lvi8eZ6JvqqxMQ==";
    };
    "js/jquery.form.js" = fetchurl {
      url = "https://github.com/jquery-form/form/raw/cfd9c57a502bd12cce4d00ade717dcac6fee6db1/jquery.form.js";
      hash = "sha512-IMpIlZCOtmvCMfOB0c9AmK6rBbvin8DbEr0fiUIyEhzLJFgNuHQsfvGjl2mXrNz80PaByM+ckiYhjNFhzmo9zA==";
    };
    "js/jquery.layout.min.js" = fetchurl {
      url = "https://layout.jquery-dev.com/lib/js/jquery.layout-latest.min.js";
      hash = "sha512-kBA+j26xHcSGvJvvP2Wm4nzIPXSVabGfeM+U/PcB1grzVmV6H7b+uisAYA+lsKP7iI4rvdyJ83CIac874VpBHg==";
    };
    "js/jquery.layout.resizePaneAccordions-latest.min.js" = fetchurl {
      url = "https://layout.jquery-dev.com/lib/js/jquery.layout.resizePaneAccordions-1.2.min.js";
      hash = "sha512-mC0fXGmUcplIj+rIew/vqaeTPPx7GIVkB3fpDEA+QfJpwbeCkOTEjLGyCmKmGNQW0Vp9RjH/LrgOzAsoBRWlCA==";
    };
    "js/jquery.optionTree.js" = fetchurl {
      url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/jquery-option-tree/jquery.optionTree.js";
      hash = "sha512-jntiBhxoAqjTpy3rfsbyK+kwr7N//F4IABMMFAZlt3VHkWCXoVrd0H4Q9gy2j4b56DhJXVTh6qFCYJpUOWmcWg==";
    };
    "js/jquery.textarearesizer.js" = fetchurl {
      url = "https://github.com/gouten5010/jquery.textarearesizer/raw/dfdb395a3b250c41f9aff681e9deafa750a85e50/jquery.textarearesizer.js";
      hash = "sha512-Ltr/MpYdIrQhx+CMz/3vNQDuPCI6WweogFAEn9gotMBcUPYCXxn2EK0Gqvsf4p8MioUHBAkRWcaIEsL5d/OFhw==";
    };
    "js/jquery-1.12.4.js" = fetchurl {
      url = "https://code.jquery.com/jquery-1.12.4.js";
      hash = "sha512-jKxp7JHEN6peEmzmg6a7XJBORNTB0ITD2Pi+6FUkc16PCaNAJX2ahZ1ejn1p1uY37Pxyirn/0OMNZbITbEg3jw==";
    };
    "js/jquery-2.0.3.js" = fetchurl {
      url = "https://code.jquery.com/jquery-2.0.3.js";
      hash = "sha512-dRkH0Y8hsCAHQDEKMuatuvYenMj+FLiUKLbwaKe952wo+xqq/B2+HNlhagtcKYY1WwMFrvTI170oFNZ0UHlJPg==";
    };
    "js/jquery-migrate-1.4.1.js" = fetchurl {
      url = "https://code.jquery.com/jquery-migrate-1.4.1.js";
      hash = "sha512-a5BK2Ye3oHZMg5Y/nRnz+4XovIcHCKkwa8dHYVtbwPATx2kqMb6fMAg5fNWiWXK4PZPFAqO1ykbWdDofdEpBZg==";
    };
    "jquery-ui-1.12.1" = fetchzip {
      url = "https://jqueryui.com/resources/download/jquery-ui-1.12.1.zip";
      hash = "sha512-SsuIvuolutgpOU9O2YWxw3btHHiAL8N9GJpB4YbB6HMPl1fnhs4eqbXliFvcoNnBF/mIgAtbcD6RjSNVseznKw==";
    };
    "plupload" = "${fetchzip {
      url = "https://github.com/moxiecode/plupload/archive/refs/tags/v2.1.1.tar.gz";
      hash = "sha512-oXfvX9015m0o0flbXwYrPS+S192DsxC0VlaoJ143b3jiNleXbgzI23/8t4yVMGv7DEHGL6mreqdoS/lb5AhHow==";
    }}/js";
    "jquery.ui.plupload" = "plupload/jquery.ui.plupload";
    "js/jquery-ui-1.12.1.js" = "../jquery-ui-1.12.1/jquery-ui.js";
  };

  commands = lib.trivial.flip lib.attrsets.mapAttrsToList paths (path: file: ''
    mkdir --verbose --parents "$(dirname "${path}")"
    ln --verbose --symbolic "${file}" "${path}"
  '');

in

runCommand "static" {} ''
  mkdir --verbose --parents "${placeholder "out"}"
  cd "${placeholder "out"}"
  ${lib.strings.concatStringsSep "\n" commands}
''
