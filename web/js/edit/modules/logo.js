/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function setImage(path){
    $("#previewlogo").attr("src", path);
}

function deleteLogo(path){
    if (confirm($("#delquestion").html())){
        $.get('/edit/edit_content?id='+id+'&tab=logo&action=delete&file='+$(path).parent().parent().attr('id'), function(data) {
            if (data=='ok'){
                o = $("#logo").children().get(0);
                if (o.getAttribute('src')=='/file/'+id+'/'+$(path).parent().parent().attr('id')){
                    o.setAttribute('src', '/img/empty.gif');
                }
                $(path).parent().parent().remove();
            }
            return false;
        });
    }
}

function setLogo(){
    $("#logofield").val($("#logo").children().get(0).getAttribute('src'));
    return false;
}

$(document).ready(function () {
    showDebugMessages: true;
    sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content"},
        north:{paneSelector: "#navigation_content", size:230,resizable:false},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0},

        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed,
    });
    $('#scrollcontainer').css('top', $('#operation').position().top + $('#operation').height());
});
