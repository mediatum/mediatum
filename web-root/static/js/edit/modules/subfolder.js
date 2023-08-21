/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

var htree = parent.gethometree();
var ctree = parent.getcoltree();

$(document).ready(function () {
    sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content"},
        north:{paneSelector: "#navigation_content", size:110,resizable:false},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0},

        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed
        });
    $(function() {
        $( "#sortable" ).sortable({
            update: function(event, ui) {
                $.ajax({
                     type: "POST",
                     url: "/edit/edit_content",
                     data: "id="+id+"&tab=subfolder&popup=popup&order="+$("#sortable").sortable('toArray').toString()+"&csrf_token="+csrf,
                     success: function (data) {
                         $("#sortable").html(data);
                         parent.reload_tree_nodes_children([ctree, htree], [id]);
                     }
                 });
            }
        }).disableSelection();
    });

    $("#sort").button().click(function(){
        $.ajax({
            type: "POST",
            url: "/edit/edit_content",
            data: "id="+id+"&tab=subfolder&popup=popup&sortdirection="+$("#sortdirection").val()+"&sortattribute="+$("#sortattribute").val()+"&csrf_token="+csrf,
            success: function (data) {
                $('#sortable').html(data);
                parent.reload_tree_nodes_children([htree, ctree], [id]);
            }
        });
    });
});
