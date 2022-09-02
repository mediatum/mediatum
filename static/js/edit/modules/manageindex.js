/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

var schema = "";
var field = "";
var values;

function changeScheme(id, action){
    schema = action;
    document.getElementById("indexfields").innerHTML = '<br/><img src="/static/img/wait_small.gif"/>';
    document.getElementById("indexvalues").innerHTML = "";
    getEditPage('indexfields', id, 'manageindex', 'indexfields__'+action);
}

function getFields(id, action){
    field = action;
    document.getElementById("indexvalues").innerHTML = '<br/><img src="/static/img/wait_small.gif"/>';
    action += "__"+schema;
    getEditPage('indexvalues', id, 'manageindex', 'indexvalues__'+action);
}

function getCurrentCollection(obj, id, action){
    document.getElementById("currentcollection").innerHTML = '<br/><img src="/static/img/wait_small.gif"/>';
    action += "__"+schema+"__"+field+"__";

    for (var i=0; i<obj.options.length; i++){
        if (obj.options[i].selected==true){
            action +=encodeURIComponent(obj.options[i].value)+";"
        }
    }
    getEditPage("currentcollection", id, 'manageindex', action);
}

function setValue(val){
    document.getElementById('new_value').value = val;
}

function checkForm(){
    if (document.getElementById('empty').checked){
        if (document.getElementById('old_values').value=="" || document.getElementById('new_value').value==""){
            return false;
        }
    }
    return true;
}

$(document).ready(function () { // set correct height of scrollable content
    var sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content", onresize: $.layout.callbacks.resizePaneAccordions},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0}
    });
});
