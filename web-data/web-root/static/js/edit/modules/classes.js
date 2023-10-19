/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function setFolder(){
    //markFolder(true, "", this.id);
    changeValue(this.id);
    return false;
}

initTree({'idOfFolderTrees': ['classtree'], 'style':'classification', 'multiselect':true, 'contextMenuActive':false});

$(document).ready(function () { // set correct height of scrollable content
   $('#scrollcontainer').css('top', $('#operation').position().top + $('#operation').height());
});

$(document).ready(function () { // set correct height of scrollable content
   var sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content", onresize: $.layout.callbacks.resizePaneAccordions},
        //north:{paneSelector: "#navigation_content", size:60,resizable:false, closable:false},
        north:{paneSelector: "#navigation_content", size:110,resizable:false,},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0},
        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed
        });
    $("#accordion").accordion({heightStyle: "pane"});
});
