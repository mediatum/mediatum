/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

$(document).ready(function () {
    $('#body2').layout({
        north: {
            paneSelector: "#navigation",
            closable:false,
            resizable:false,
            spacing_open: 0,
            showOverflowOnHover: true,
        },

        south: {
            paneSelector: "#sub_footer",
            closable:false,
            resizable:false,
            spacing_open: 0,
            spacing_closed: 0,
            size:60
        },
        center:{
            paneSelector: "#sub_content"
        },
        resizerTip: js_edit_layout_resizertip,
        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed
    });
});
