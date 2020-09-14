/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function Thumb2Window2(id) {
    var win1 = window.open('/thumbbig?id='+id,'thumbbig','width=100,height=100,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=1');
    win1.focus();
}

$(document).ready(function() {
    sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content"},
        north:{paneSelector: "#navigation_content", size:110,resizable:false},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0},

        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed
    });
});
