/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

var onj_name = "";
function init(name){
    obj_name = name;
    o = document.getElementById('value');
    if (window.opener && !window.opener.closed){
        o.value = window.opener.document.getElementById(name).value;
    }
    o.focus();
    var currentfolder = o.value;
}

function save(){
    value = obj_name;
    if (window.opener && !window.opener.closed){
        window.opener.document.getElementById(value).value=document.getElementById('value').value;
    }
    window.close();
}

function setFolder(){
    n_node = document.getElementById('Node'+this.id);
    if (n_node){
        t = n_node.getElementsByTagName('A');
        $('#value').val($('#value').val().replace(this.id+';', ''));
        if (t[0].style.backgroundColor=="" && t[0].className==""){
            t[0].style.backgroundColor = "#ccc";
            t[0].getElementsByTagName('input')[0].src = imageFolder + checkImage;
            t[0].getElementsByTagName('input')[0].backgroundColor = "";
            $('#value').val($('#value').val()+this.id+';');
            return false;
        }else{
            t[0].style.backgroundColor = "";
            t[0].getElementsByTagName('input')[0].src = imageFolder + uncheckImage;
            t[0].getElementsByTagName('input')[0].backgroundColor = "";
            return true;
        }
    }
    return false;
}

var currentfolder = '998779';
initTree({'idOfFolderTrees': ['classtree'], 'style':'classification', 'multiselect':true});
