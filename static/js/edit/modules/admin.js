/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function openForm(){ // show upload form
    $('#mediatum_addform').css('display','block');
     parent.$('#overlay').css('display', 'block');
}

function openFilledForm(obj){
    $('#new_name').val($(obj).attr('name'));
    $('#new_value').val($(obj).attr('value'));

    $('#mediatum_addform').css('display','block');
    parent.$('#overlay').css('display', 'block');
    return false;
}

function closeForm(){ // close upload form
    $('#mediatum_addform').css('display','none');
}

function setActionType(value){
    $("#type").val(value);
}

$(document).ready(function () { // set correct height of scrollable content
   var sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content", onresize: $.layout.callbacks.resizePaneAccordions},
        north:{paneSelector: "#navigation_content", size:50,resizable:false, closable:false},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0}
        });
    $("#accordion").accordion({heightStyle: "fill"});
});
