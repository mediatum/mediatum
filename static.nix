{ pkgs ? (import ./nixpkgs.nix {}).pkgs
, lib ? pkgs.lib
, fetchurl ? pkgs.fetchurl
, fetchzip ? pkgs.fetchzip
, runCommand ? pkgs.runCommand
}:

let

  paths = {
    "ckeditor" = fetchzip {
      url = "https://github.com/ckeditor/ckeditor4/archive/refs/tags/4.4.6.tar.gz";
      hash = "sha512-o8HGv6zwwSY1m7Nf1nj/MkmvunjI9KSaB5RRg06qSrMI7J0PsPGqFJpUNBFlREmOR6NMgCYrEq6982+3vOi9Yg==";
    };
    "fancytree" = fetchzip {
      url = "https://github.com/mar10/fancytree/archive/refs/tags/v2.4.1.tar.gz";
      hash = "sha512-O3AP9eu6ONtsCI1BOp2JlhiEpFKOzejeZLQ2KoChd9BKXan7CWsgkfGbuDRiE/wD3QWwEGv+Lvi8eZ6JvqqxMQ==";
    };
    "js/jquery.form.js" = fetchurl {
      url = "https://github.com/jquery-form/form/raw/cfd9c57a502bd12cce4d00ade717dcac6fee6db1/jquery.form.js";
      hash = "sha512-IMpIlZCOtmvCMfOB0c9AmK6rBbvin8DbEr0fiUIyEhzLJFgNuHQsfvGjl2mXrNz80PaByM+ckiYhjNFhzmo9zA==";
    };
    "js/jquery.layout.min.js" = fetchurl {
      url = "https://cdnjs.cloudflare.com/ajax/libs/jquery-layout/1.3.0-rc-30.79/jquery.layout.min.js";
      hash = "sha512-p0MGIH84Td1hpoLDySvTeIiiOA0bJkpQZZGoQlh7l31tQKIQmkzjS7HxLrpsFlpGGmIpJmP0hL+SUHuT6QlzSg==";
    };
    "js/jquery.layout.resizePaneAccordions-latest.min.js" = fetchurl {
      url = "http://layout.jquery-dev.net/lib/js/jquery.layout.resizePaneAccordions-1.2.min.js";
      hash = "sha512-AVKXbn647MwXnhZEqHxj/niPkpKOfcWh+ht8lIoJF8N4sscEGtQcx4FnQUdrSKgqeizQOAQqh3L4zuEmu/FSSw==";
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
    "plupload-js" = "${fetchzip {
      url = "https://github.com/moxiecode/plupload/archive/refs/tags/v2.1.1.tar.gz";
      hash = "sha512-oXfvX9015m0o0flbXwYrPS+S192DsxC0VlaoJ143b3jiNleXbgzI23/8t4yVMGv7DEHGL6mreqdoS/lb5AhHow==";
    }}/js";

    ############### icons ############################

    "img/admin.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=ruota_dentata_grigia_2_01r.svg";
      hash = "sha512-I4beG2L6lyeZwRV3KLGcX9Csl1LaLiwYVOynTZ/YgUF5fzCajplG/QXXvGTiztijIUtRx+7PCivQL3FAU6brtQ==";
    };
    "img/alert.svg" = fetchurl {
      url = "https://github.com/apancik/public-domain-icons/raw/df284bf4bbd52becf5d3cf73791660e3f538a1e3/dist/symbol%20alert.svg";
      hash = "sha512-CCvbR3hVJiKxn5uBEsYiLnuv1JzKq+KbHA0oib/SyksckF47N4m3nu2Q8syVfe7qyDXB2YSIUjydx3FF8mOjgQ==";
    };
    "img/arrow-left.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=matt-icons_go-previous.svg";
      hash = "sha512-Xh8KHfw1aQ1gaZnNZsy5uoenMEQCxSAbh/gUPpuChgd0g1SXiQRGvzxfA3AHIQYAVHyp8gme38kK4RD7eV48BA==";
    };
    "img/arrow-left-end.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=matt-icons_go-first.svg";
      hash = "sha512-1HfpTwXeLnS9b9lp3GpDA0qmeiBbDMAwg4PS/Ci/7SoSzQizjaI6JAFzVDavqhsLGbHx0xy0md00/3liTrEMYA==";
    };
    "img/arrow-right.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=matt-icons_go-next.svg";
      hash = "sha512-sGyIN5CPKR0ZiPkGK5qR0dBquqZs/and97mpPfQab7dFAlrMOqRVJ96aXW6OwkWPgL8mM1LGykZ3EOytH73ecg=";
    };
    "img/arrow-right-end.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=matt-icons_go-last.svg";
      hash = "sha512-zdCRwjGq8xW22CWkobQdJ2echA7lrEFVMeAFPfLsppR+fO3OexoXuQymo+z5V1IKII9l+nD8GahkYJZnU3QPDw==";
    };
    "img/attachment-paperclip.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=Icon_Documents.svg";
      hash = "sha512-bABd3dA6sYb9T4x+WODBxDrPtXg18V8bB+BqDmXex/BudadsYzYNzEWuBRU1YPlDLw214ZLVaKYt5oGH3ojjEg==";
    };
    "img/avi.svg" = fetchurl {
      url = "https://github.com/sempostma/cc0-file-icons/raw/6a216fdb638583744321b9fa76e4244ca4f54b05/background/svg/avi.svg";
      hash = "sha512-OxHwCg7+Qin/A7rm/ojprXOqCf+ZirBCQw7kXyYK5ofyO3EiwG4bYbuw2np4GSmdgFPC6zDvslhLdDgrtuIkuQ==";
    };
    "img/back.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=mono-rotation-acw.svg";
      hash = "sha512-KwRvJYg7gv2M9XgmfrI+KmUQpiDjwrGayZVj+7Mopol6RHVjmpZmxFabK8H+s402cSCVnsHRqoPgUczK3G9eYQ==";
    };
    "img/bmp.svg" = fetchurl {
      url = "https://github.com/sempostma/cc0-file-icons/raw/6a216fdb638583744321b9fa76e4244ca4f54b05/background/svg/bmp.svg";
      hash = "sha512-r5zpINeXDviAIl6UyBV9roctfuz8xk6RaPQ9kAGUezZisVjbHUFVOAJsgtYDqE6QmGJpFwX0Gv/Mr7pjjxZkiA==";
    };
    "img/box.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=rodentia-icons_emblem-minus.svg&disposition=attachment";
      hash = "sha512-BLGj1w5qIt7uUa9ZdqxQ5EzbbmBQOplJxRawLgEyunmpDD05E4NcuQmG34aT7rNl6S/O18z9M3xDwasOPk72bQ==";
    };
    "img/boxx.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=dev.svg";
      hash = "sha512-du30dFFbVY43ZFh8WKumoWy73+LY3MypFbmWQ+6O6zENJVgYaNjxJL5l3T2HEwWoON6kE4AhAOQKhtLBjQgkJQ==";
    };
    "img/cancel.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=matt-icons_cancel.svg";
      hash = "sha512-HR+hnTO2OPCKOY8K+Wj84lvmqe7YVVN7g1j66AJVxmkRSFJ4XRKJeKDycjLeKUByDmP8lpUFwgRlknzljDf9Rw==";
    };
    "img/webtree/check.svg" = fetchurl {
      url = "https://github.com/davidmerfield/Public-Icons/raw/07922fc7b64eb6277edcc7983802353d0f42786d/source/icons/check.svg";
      hash = "sha512-RbUgGyT0JYU+kbe1/LdS/tytL2pOn1cBjjQL4NtdLUp2HxSwHXWnBU9B9IU8HlHdmWXj6OJVX393HrxNOnsPxw==";
    };
    "img/clone.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=ftcopy.svg";
      hash = "sha512-gO/Q9zLP9MzWIOtSostYfnztmqGIrKTp1f/uV9zIgp6XhQ2vxGKa+S5A8CCfUb5Vk1gHvoPROVvjzsA7wKBNRw==";
    };
    "img/content-list.svg" = fetchurl {
      url = "https://www.svgrepo.com/download/286574/list.svg";
      hash = "sha512-Eg1AWI4LYjDoQ4WooVEexBMw1EksveCsTD/vU2xw40B6Ki75LwRS1aPkCCnCoHpzivQu5fDsl+NvFcignuRPKQ==";
    };
    "img/webtree/collection.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=folder2.svg";
      hash = "sha512-uzPZ9N9Vw9K8in+ck+mqTgBgdnPrJQKPWOEIRyR1e40sSTZBi2jZ366tLJRT25FJMRiBkx5j2tblVY/Q174gTg==";
    };
    "img/document.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=matt-icons_text-x-doc.svg";
      hash = "sha512-IigJrhwE3/26NWGg0AjjSx3OlbH4XJbdoQhvIecNhMVLnK9ga+fNBDSlQQhcMUbYlE8sufAsZ7nWSshdsQfNcw==";
    };
    "img/editor/document-new.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=file-add-icon.svg";
      hash = "sha512-dd0mTqD01hC4DILZPJmKkgmse6+kvlCwalfRaLYk/Rqxi9snrE2u+0bVYGse3MmXivKl5di5QgZqL6SeZ1Hwkw==";
    };
    "img/webtree/directory.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=1279643371.svg";
      hash = "sha512-zOBljLJD8wS9uaWYjzI7FLwbRuG9H4rl6/qoRIOIzNPwOeHIqPvU8N47I5Uw6KNaJbfljoRUmzS+nIUYHW3gwg==";
    };
    "img/editor/doi-logo.svg" = fetchurl {
      url = "https://upload.wikimedia.org/wikipedia/commons/1/11/DOI_logo.svg";
      hash = "sha512-m0OrxUeXESURB1gM9oiyARAn+CxPR9YU6mJ1IMIgdveY/KKtUbCwXniRtIXnSdrLKTSiGdxtfPktLstJG7NA8w==";
    };
    "img/downarrow.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=tango-down-arrow-blue.svg";
      hash = "sha512-ltpZjQBmsctzb5bJyl1ZQaIjaxddHrUUkTL7dbmmfma50Hs/h9iFC1vrQu29+dZ3YIWRTpg0bGnpXNCAwhZFgQ==";
    };
    "img/downarrowdisabled.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=1313159889.svg";
      hash = "sha512-sw2r8BoWONNeaVFjeEOcv9Ta8/C3Z0o/anb4V8f6roMjL304gQxyeP8gZtui/5RTcRhO+KnXle5s66J24JqvdA==";
    };
    "img/webtree/download.svg" = fetchurl {
      url = "https://www.svgrepo.com/download/313131/download.svg";
      hash = "sha512-avLL4+U3UFpnGb8em2HoEMFwQtrPhb7aWRSYXByQoEbXsIKrTQ3HuBrvdN/TLzsVihcqQJ9jAhgNXoj5E+ZZuA==";
    };
    "img/edit-pen-paper.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=MajinCline_Notepad.svg";
      hash = "sha512-Ve7S6voRbPtCi+5Kqgjsh+t4YRIntV2UjkULNGJ2pUIa7MjPBhZvvx3sDy2KP03Z466ZW4BjbH7ib4psM6aqNw==";
    };
    "img/edit-all.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=edit-copy.svg";
      hash = "sha512-n8+YGiiQhCUL+Y/aMG/l+J55Vc9ZBODRZn093m65iNSgJntye+57AVtz+lNKY/log+ylA0/OWbq+IzeG8HRBaw==";
    };
    "img/email.svg" = fetchurl {
      url = "https://github.com/davidmerfield/Public-Icons/raw/07922fc7b64eb6277edcc7983802353d0f42786d/source/icons/envelope.svg";
      hash = "sha512-GcC25esiJsHpzGp0oxwzck/TfajHWRgGMEuDxrNmWzXNTkayTp5UFkFkhCLQVA3PYK7CpV0GXXLSsay34+0GiA==";
    };
    "img/export.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=export.svg";
      hash = "sha512-bchxl8F6m6Fk8HNr6Tx0ozBpEwXpjJOxNQrB4JlMwii5WUtO+AW8sDZiLbngsxRaQDHY3em6pL7vtSd+4UK7wA==";
    };
    "img/extlink.svg" = fetchurl {
      url = "https://github.com/davidmerfield/Public-Icons/raw/07922fc7b64eb6277edcc7983802353d0f42786d/source/icons/external.svg";
      hash = "sha512-8E/yNPfHEL8GXAIN1ubgK3ZeqNRKN9ny8Isa5mwE0CXBbpFVHcAuW0wu5VZ+++e82C8C7XqrL3JjvymfqN+iyg==";
    };
    "img/editor/eye.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=Eye4.svg";
      hash = "sha512-NGTxCW9uZ8mYUIWdLKAXvQp+a9rh56kcFgNUK0IFtSa0RhT9OztgSc0hvgldbVyJoYEn2KRhIV7lHJ+qem3hqg==";
    };
    "img/file.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=file-icon.svg";
      hash = "sha512-7ykZcQuwUj+jOfVxLB1qD14vWvysxxs76SEEV/Qp9KpGlUhjBHILQ0Ul7KH4xwDzuisl4UJbrXGe+tfeBY5hlg==";
    };
    "img/editor/file-new.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=new.svg";
      hash = "sha512-dS/zkR9BhCTplGM1XvmW914rZtFILHAUV9Y70tSc4/qAuCMT1PADRkpIpFIgTt+Yx53MBMAEZ4Mj3hRd+WNLFw==";
    };
    "img/flag-de.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=rodentia-icons_flag-de.svg";
      hash = "sha512-RpQMWT28cEHXo88w2sXA6MRx/TLVX+W4NMobtB4HTiVHig6VFN1Q8/TcQ1rhu/tTzR2/iQJbqgTUsTol44fAMA==";
    };
    "img/flag-en.svg" = fetchurl {
      url = "https://upload.wikimedia.org/wikipedia/commons/8/83/Flag_of_the_United_Kingdom_%283-5%29.svg";
      hash = "sha512-tG2equUPyF6yYLpkwyV/PKdJdE+n8xL3ezpYGFs3sgLAKRfRd9JgjmQvnTWHBhuh9WZZirRLTs5+rVNdM23LRg==";
    };
    "img/folder-plus.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=pitr_green_double_arrows_set_1.svg";
      hash = "sha512-jgBt25yCWXQBcusHiQs7B9StLZp+Gxx0M4YgszpDyMiYxtsVriSZehc8KqkuA3zfL/xgTLdDB3/D4KlIZldhrg==";
    };
    "img/gif.svg" = fetchurl {
      url = "https://github.com/sempostma/cc0-file-icons/raw/6a216fdb638583744321b9fa76e4244ca4f54b05/background/svg/gif.svg";
      hash = "sha512-8FIpDO37X5eIGF0XfafYSR2p6OcDpa6DI4XdcT7egWMtGV6KTraCnWOvUbSnOuIidmu6dipIOJBNGCvY5qSIiQ==";
    };
    "img/greyarrow.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=fttab-right.svg";
      hash = "sha512-ICdqDgFF5oqEQp5k4y8yodiX/s7Oc0fEwrRqE0qlEpoORGlAPxCyF5DT3Uge9V1R28VfLfHBXi0AU5NH/3kEbw==";
    };
    "img/people-group.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=group.svg";
      hash = "sha512-/3RFK2XEIu8NdvNDpbK1ugX4oH4qsHUfeA7XfpsHc0f3iWa6MBPYtbieY2EygksQlpZne4s4oiB5hhpXzgoHwQ==";
    };
    "img/webtree/home.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=rodentia-icons_user-home.svg";
      hash = "sha512-usPA0wbV45sw/I0PVJn5xcAtgTwxvpq93oBx52v+SMCPu7bSPmxbX0r9S5rE4prPSwCKFb9FQjnZJePvxNb5DA==";
    };
    "img/install.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=jean_victor_balin_add.svg";
      hash = "sha512-WHK+cEK+rYnbnfBdH5tssTAsjDwEKZADQL8fARx4JNO45Y2FifJHHp/q2Gyq2TukJJpjRDzGfGjqgDi9YxRxUg==";
    };
    "img/jpg.svg" = fetchurl {
      url = "https://github.com/sempostma/cc0-file-icons/raw/6a216fdb638583744321b9fa76e4244ca4f54b05/background/svg/jpg.svg";
      hash = "sha512-xiX5hE3xBuvLilfjif4GOFdyyLx2wHkTKVq8xZ5XYkbAvBso6trNBiMBm6D8KK/CfoqK+40hT63OVqYNggVT5g==";
    };
    "img/login.svg" = fetchurl {
      url = "https://github.com/davidmerfield/Public-Icons/raw/07922fc7b64eb6277edcc7983802353d0f42786d/source/icons/entrance.svg";
      hash = "sha512-sQ3meMYd/QlxL8KWw10RKo2eGOIHTH7X/y1ug4qnJFAKFtwkx8iQmKVfn6fWcdSCn/QgEfnnOpQdTY4iBmdtaw==";
    };
    "img/logout.svg" = fetchurl {
      url = "https://github.com/davidmerfield/Public-Icons/raw/07922fc7b64eb6277edcc7983802353d0f42786d/source/icons/exit.svg";
      hash = "sha512-ekY5v19lcLZjPw4qxYTR7KZHSTyOR8Us56YQQyuRg77zG9IKEbD1wt/pn4J4pDRJ+FT74iKeUOfu26LSTnzYqw==";
    };
    "img/webtree/minus.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=ftedit-remove.svg";
      hash = "sha512-Dd3CNILpihjDut2kYUPf7kD8XW3CdcAP7PPsVrdC4RmmydxFCcyR108/DQPOyowc8jxij1rC84OQ5Y7VTwZJpw==";
    };
    "img/editor/move.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=ftmove.svg";
      hash = "sha512-LOvqHZ+BIytjbN0P9dVjpykqcXj4ICYd39XiZCgMfJ/QEidf7gEZ8EM+87JbwJWWxgCgZkdfOPG0hwZi1ju5XA==";
    };
    "img/mpg.svg" = fetchurl {
      url = "https://github.com/sempostma/cc0-file-icons/raw/6a216fdb638583744321b9fa76e4244ca4f54b05/background/svg/mpg.svg";
      hash = "sha512-PK44PCpBKVmUpeRgXWyBZ45fMO8maxRCzMQ2oykbo0RdkLYgQzaLyV+n7wNlKPjCBzvLVmBoLcCoMw5q32JC4A==";
    };
    "img/msword.svg" = fetchurl {
      url = "https://upload.wikimedia.org/wikipedia/commons/f/fb/.docx_icon.svg";
      hash = "sha512-TZsuX+OBkpEHugDntlH+LXZuF3egbpGR7k3QQ54KMxp4o+JurO1A+weyPzAxEOgC49I6/7OB3uLeYlHRJIZnJw==";
    };
    "img/editor/navigationtree.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=6d5ed7ec.svg";
      hash = "sha512-rF7BUc8l58JqWr2Ar4zl14q9kZ6NMRrNOKgf059HLSgPcHK7zIqwQMfdDEQuanZgnNwAIg374L7OD57apHhD9Q==";
    };
    "img/padlock.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=Padlock-gold.svg";
      hash = "sha512-BFXAy7TuVv8iXGYGtfV/2BcFc8xWT1F5Nt7IrUeAjictiwl6SZ41CberxB1lK9wlqqQmXmfIe4QYudGW9CIKsw==";
    };
    "img/pdf.svg" = fetchurl {
      url = "https://github.com/sempostma/cc0-file-icons/raw/6a216fdb638583744321b9fa76e4244ca4f54b05/background/svg/pdf.svg";
      hash = "sha512-HHN1e1vw4UUNHpJl5NhJVvlolPszykThoPJCcTlXj8RSAtNVYzUS4wX4vj3kpbxcG0lZtFxPDUygYHpcEgtopw==";
    };
    "img/webtree/plus.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=ftedit-add.svg";
      hash = "sha512-AXTwqMihdrMf3r4q1eZT4PStGNIw1CjS2Wzzg6VaYJoTsKD9B3bz4cnj2QBn2KQkY3fmZlMIagR098kyTzfG2w==";
    };
    "img/png.svg" = fetchurl {
      url = "https://github.com/sempostma/cc0-file-icons/raw/6a216fdb638583744321b9fa76e4244ca4f54b05/background/svg/png.svg";
      hash = "sha512-0n+5YZ2Wvaj4TZXxsNNkCCqksjggbri5aDe4ig1aIYgf7P/HkmlZ0mXXkF9ctbvDcfx7CApPxodbXxZl+09k+g==";
    };
    "img/ppt.svg" = fetchurl {
      url = "https://github.com/sempostma/cc0-file-icons/raw/6a216fdb638583744321b9fa76e4244ca4f54b05/background/svg/ppt.svg";
      hash = "sha512-fgzofTZTnOJBfQfm2MKjMszdZCbCtU9cZi2o8vDfal7xG9sRQ23Y1fEqWfPgHLSbOA1r9ZLJuBplldjqe4lxJw==";
    };
    "img/printer.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=warszawinka-printer.svg";
      hash = "sha512-bC/WCSxqDtu8NJ08GWqgpBpsn/s9XXd40YS+KOL1aLXwzJH4RS11jnA+iBW3+NgPR5eY8Dzc8wHZ+D1IfGzCmA==";
    };
    "img/ps.svg" = fetchurl {
      url = "https://github.com/sempostma/cc0-file-icons/raw/6a216fdb638583744321b9fa76e4244ca4f54b05/background/svg/ps.svg";
      hash = "sha512-Qiha9J3QtJy5SWzoAVQBOsA80TjGTL3GojaalgPARe2Dn3NNOPS4TcwLCzKWY0erI5RHrhM75iDjGohx530XEQ==";
    };
    "img/magnifying-glass.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=Magnifying-glass.svg";
      hash = "sha512-RQhpttogkMF8RVgXMo10oPi7mBQWkcn4Jan10aMHDU4MCQwnRX9Tmt+05/4dhY8kEqu1w3vL1onID4peNL1dRw==";
    };
    "img/editor/settings.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=niceboy_Mixer.svg";
      hash = "sha512-X/EFljW9X0Ub6xvy3RV3cBLPmXNfJoIK0LRGQ5eihmhm3t1nUoFdqEN58xryzfgp0C+Dqv58klxZvrX4BC1uyQ==";
    };
    "img/editor/settings2.svg" = fetchurl {
      url = "https://github.com/apancik/public-domain-icons/raw/df284bf4bbd52becf5d3cf73791660e3f538a1e3/dist/symbol%20gear%20settings%20preferences.svg";
      hash = "sha512-wIet7CaqdWQ5zexamB2BYLVMhKwz9WJdkKIKDJkVu8uJZ8mHetjZUCgcuym3LnT25PUh8TmoixtFMSPUXWX1UQ==";
    };
    "img/webtree/sheet.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=file-icon.svg";
      hash = "sha512-7ykZcQuwUj+jOfVxLB1qD14vWvysxxs76SEEV/Qp9KpGlUhjBHILQ0Ul7KH4xwDzuisl4UJbrXGe+tfeBY5hlg==";
    };
    "img/editor/sort.svg" = fetchurl {
      url = "https://www.svgrepo.com/download/181276/sort-arrows.svg";
      hash = "sha512-4QJ/VGN+GtL7/k3ITJ3qv5xpqapEwfNJs8rrwIh++EwGi5S/jOMT+knxCWoU6lSy7BNW0zFCV2ZRdj6bpBdyEg==";
    };
    "img/sort-by-alphabet-az.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=ftsort-incr.svg";
      hash = "sha512-DvJS0cZvnvDutDiyGpxKzvB4fiUGAEJvmd9Uh1aRtyNOoiuaHhr5BQPrOvy0hZ4T4NO4q05IU0TThkNuiWWp4w==";
    };
    "img/sort-by-alphabet-za.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=ftsort-decrease.svg";
      hash = "sha512-Ke2ZIlzF2YS4HmwfXcK6c8R/sfJHaUcGN1N6uBflgVXe0rP+HEGtc7hzHxUDuNWpJnVN6rlYUOQda6rm5oTH3A==";
    };
    "img/stylelist.svg" = fetchurl {
      url = "https://www.svgrepo.com/download/258665/list.svg";
      hash = "sha512-PJmOy9fDtjcgoU3ZWKT0UhJuLMUySkQ/uACkIRrtm5PaioLnmeE2O0D1czewr4ONMUDJycL+DSpRlgFFlhdC5g==";
    };
    "img/text.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=rodentia-icons_text-x-generic.svg";
      hash = "sha512-nMmbKBs2fZVjO5edh73+X19dkX1nYJ4RSvy+oejxw0pDpAcPYQ1yevO2Z96Rxh/KWvFa7xRTSmnwauN4NaIVKw==";
    };
    "img/thumb.svg" = fetchurl {
      url = "https://www.svgrepo.com/download/174027/four-squares-button-of-view-options.svg";
      hash = "sha512-l9IKI2K3M4N3dsSCKqCKYPBWrORqkr4Wem6gg/tAWOXzpcXlK1m91zq1TChoxwDpLKnlcztUFM4NaOgmsCG+UA==";
    };
    "img/tiff.svg" = fetchurl {
      url = "https://github.com/sempostma/cc0-file-icons/raw/6a216fdb638583744321b9fa76e4244ca4f54b05/background/svg/tiff.svg";
      hash = "sha512-7Dtm/JUMLCd7R54/Xn3HAcpfYNPPFxjVvbyyY28I6uIRB9Pqj2+c2RrFaI0YRFnJHDxPqKQkzvQg16zz2uqbMg==";
    };
    "img/tools.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=preferences-system.svg";
      hash = "sha512-yiSxPpAW2/imzlPofFWo0A2kdLFG/ikpI+ZayR3tqF4Lnh6JqDDJLUau6fKveBe7wZGYRRZNRpJW7ll04Cdqsw==";
    };
    "img/webtree/trashbin.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=Anonymous_Architetto_--_Cestino_vuoto.svg";
      hash = "sha512-aKhPLlpjbWlQ7MIH8tTHEBHSWWRTqNiD44f6qHSCBmkoq8JytOPOiVkvmjtq3qYV2kTykvGWxCHFtbdN/PY94g==";
    };
    "img/webtree/transparent-pixel.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=ftemptybox.svg";
      hash = "sha512-acGwuxlXT/+l6nPWZ2fEjwmx/E0jhgr+5vde99zyCtB2jGZn/DWgLTkBzgu4epHwTT+rSaYLm/VKb3P/BFyWhA==";
    };
    "img/up.svg" = fetchurl {
      url = "https://www.svgrepo.com/download/142150/up-arrow.svg";
      hash = "sha512-wLQjFaM6d/UJL1B28Wun2WIpfIbeNHo4JxtpvmiN1NZlwppYsQKomf2KPVdJaUqJ988TjT8YWbGFAzcrjiFLTQ==";
    };
    "img/uparrow.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=tango-up-arrow-blue.svg";
      hash = "sha512-XW10zi2Is4a2zY/+8lXwgB12KV157QspUTZ8MhuleyE9eX5APSWlBnaSSJKdbxeynX4XLWJuL87NE5lBsMy1cQ==";
    };
    "img/uparrowdisabled.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=1313159942.svg";
      hash = "sha512-6QUkgEww+fmFHnu9UtbNku0WXxJmLNVQvvbbqizHY/CqO0Yb/P+p6SUSz4jl1vUY0BwYrbEn2EKubHkJL65xkQ==";
    };
    "img/webtree/upload.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=pitr_green_arrows_set_1.svg";
      hash = "sha512-QOQeguGyu62X8uiz1uApBOnCNejpN/6BJcM1/AxC1gkt5qLgHKjMIV1d74UwhNBjq6YYa6TzY6liSuzdqj3VEQ==";
    };
    "img/versioning.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=WoodTextureV.svg";
      hash = "sha512-sLnPxd/W7cy2c8QHyRtowvULtu31WAbLpbpk0f8y1H1E4EYcsPHNSeNghEwUu0ccaVnru53Zi2fQKtHP9r2wjQ==";
    };
    "img/video.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=rg1024-Film-strip.svg";
      hash = "sha512-mfiWzy3mXo78KI1Yt3+gEYRenoq/kgzx18+9bJtxS6oOuPX7EI5N5vvwTNfepj4AEJ7F6SkhXI9AbBkxnAUTew==";
    };
    "img/workflow.svg" = fetchurl {
      url = "https://www.svgrepo.com/download/475025/workflow.svg";
      hash = "sha512-c0Py71btEdMEiBZX6xYysb5CxercRESQWMk4gfCO+OOX14D1W6YjVqy34wL8Prh9wlQ3u2OLoYnG2HDKqzh4xQ==";
    };
    "img/editor/world.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=provider_internetsvg.svg";
      hash = "sha512-Qp1A55yuBXnBgq//rAfcKnCDOyKf6W3aOv4/vIvaKpsspvzVV62lyDo7sJWWV5RRUAGSKjO4MxkmX9uYOlqk7A==";
    };
    "img/zip.svg" = fetchurl {
      url = "https://publicdomainvectors.org/download.php?file=zip.svg";
      hash = "sha512-nhzjjCDnLvuZHD1oSVYZyrGylF05GXUbbzN1mwka/gSZkGf+JZnwy+X6I9Ym1eMttUy9u1YZNeooZ9szsnRhUA==";
    };
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
