/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function getSelect(id, newobjtype) {
    getEditPage('schema', id, 'changeschema', 'get_schemes_for_'+newobjtype);
}

function showWait() {
    var span = document.createElement("span");
    span.classList.add("mediatum-editor-nav-image-wait");
    document.getElementById("schema").replaceChildren(span);
}

$(document).ready(function () {
    sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content"},
        north:{paneSelector: "#navigation_content", size:110,resizable:false},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0},

        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed
        });

    // icon in tree may need update ...
    if (is_container == 1) {
      try {
        var an = parent.current_tree.getNodeByKey(nid);
        var pan = an.parent;
        var qan = $(an.span);
        pan.load(forceReload=true).done(function() {
                pan.setExpanded(true).done(function() {qan = $(an.span); qan.addClass('fancytree-active');});
                qan = $(an.span);
                qan.addClass('fancytree-active');
                });

         qan = $(an.span);
         qan.addClass('fancytree-active');
      }
      catch (err) {
        consoledb.error(err);
      }
    }
});
