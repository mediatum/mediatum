/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

var items = new Array();
var itemnames = new Array();
var showContextMenu = false;

function setFolder(){
    check = markFolder(false, "", this.id);
    obj = document.getElementById('Node'+this.id);
    label = obj.getElementsByTagName('A')[0].title;
    if(!check){
        if(items.in_array(this.id)==-1){
            items.push(this.id);
        }
        if(itemnames.in_array(label)==-1){
            itemnames.push(label);
        }
    }else{
        pos = items.in_array(this.id);
        if(pos>=0){
            items = items.slice(0,pos).concat( items.slice(pos+1) );
        }

        pos = itemnames.in_array(label);
        if(pos>=0){
            itemnames = itemnames.slice(0,pos).concat( itemnames.slice(pos+1) );
        }
    }
    names = "";
    if (itemnames.length>0){
        names = "- "+itemnames.join("<br/>- ");
        $('#btn_publish').removeAttr('disabled');
        $('#btn_publish').prop('title', '');
    }
    else {
        $('#btn_publish').prop('disabled', true);
    }
    returnvalues(items, names);
    return false;
}

function returnvalues(ids, values){
    $('#destination').val(ids);
    $('#mediatum_dest_names').html(values);
}

function showForm(){
    $('#mediatum_treeform').css('display','block');
}

function closeForm(){
    $('#mediatum_treeform').css('display','none');
}

$(document).ready(function () { // set correct height of scrollable content
    initTree({'idOfFolderTrees': ['classtree'], 'style':'classification', 'multiselect':true});
    $('#mediatum_publish_operation').css('height', $('#mediatum_publish_operation').height() + $('#mediatum_publish_error').outerHeight());
    sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content"},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0},
        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed
        });
        $('#btn_publish').prop('disabled', true);
});
