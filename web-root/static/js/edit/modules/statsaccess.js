/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function showDetailAccess() {
    $("#access_all").toggle();
    $("#access_top10").toggle();
}

function showDetailAccessCountry(){
    $("#country_all").toggle();
    $("#country_top10").toggle();
}

$(document).ready(function () { // set correct height of scrollable content
   var sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content", onresize: $.layout.callbacks.resizePaneAccordions},
        north:{paneSelector: "#navigation_content", size:100,resizable:false, closable:false},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0}
        });
    $("#accordion").accordion({heightStyle: "pane"});
});
