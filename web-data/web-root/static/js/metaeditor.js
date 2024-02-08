/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

var i = 0;

function questionDel(){
    return confirm(unescape("Soll dieser Eintrag wirklich gel%F6scht werden?"));
}


function moveRight(left, right) {
    if (left.selectedIndex != -1) {
        for (i=left.length-1; i>=0; i--) {
            if (left.options[i].selected && left.options[i].value!='__special_rule__') {
                mytext = left.options[i].text;
                myvalue = left.options[i].value;
                opt = new Option(mytext,myvalue);
                right.options[right.length] = opt;
                left.options[i]=null;
            }
        }
    }
}

function moveLeft(left, right) {
    if (right.selectedIndex!=-1) {
        for (i=right.length-1; i>=0; i--) {
            if (right.options[i].selected && right.options[i].value!='__special_rule__') {
               mytext = right.options[i].text;
               myvalue = right.options[i].value;
               opt = new Option(mytext, myvalue);
               left.options[left.length] = opt;
               right.options[i]=null;
            }
        }
    }
}

function mark(list){
    for (i=0; i<list.length; i++)
    {
        list.options[i].selected=true;
    }
}

function setCancel(obj){
    obj.value="cancel";
}

function openPopup(url, name, width, height){
    var win1 = window.open(url,name,'width='+width+',height='+height+',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=yes'); 
    win1.focus();
    return win1;
}


function metatypechange(doc){
    for(var i=0; i< doc.getElementById("newfieldtype").options.length; i++){
        obj = doc.getElementById("div_" + doc.getElementById("newfieldtype").options[i].value);
        if (obj){
            if (doc.getElementById("newfieldtype").value == doc.getElementById("newfieldtype").options[i].value){
                obj.style.display = "block";
                
            }else{
                obj.style.display = "none";
            }
        }
    }
    
}

function clear_description(doc){
    obj_help = doc.getElementById("edit_help");
    if (obj_help) {
      obj_help.value = "";
    }
}

function getTypeString(s){ 
    return s.substring(s.lastIndexOf('(')+1,s.length-1);
}

function showPreview(doc, src){
    obj = doc.getElementById("image_preview");
    if (src!=""){
        obj.src = src;
    }else{
        obj.src = "/static/img/webtree/transparent-pixel.svg";
        obj.className = "mediatum-icon-small";
    }
}

function countMeta(obj, l){
    /*dummy method*/
}
