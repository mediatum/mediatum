/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

$(document).ready(function () { // set correct height of scrollable content
    var sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content", onresize: $.layout.callbacks.resizePaneAccordions},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0}
    });
}
