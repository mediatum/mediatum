/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

$(document).ready(function () {
    sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center: {paneSelector: "#sub_content_content"},
        north: {paneSelector: "#navigation_content", size: 0, resizable: false},
        south: {paneSelector: "#sub_footer_module", size: 20, closable: false, resizable: false, spacing_open: 0, spacing_closed: 0},

        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed
    });
});
