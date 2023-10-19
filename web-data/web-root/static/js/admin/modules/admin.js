/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function openwindow(url)
{
    popup = window.open(url, "popup", "resizable=1,width=700,height=450,scrollbars");
    popup.focus();
}

function showInfo(){
    document.getElementById("message").style.display="block";
}

function selectacl(objname){
    obj = document.getElementById(objname);
    for (i=0; i<obj.length; i++){
        obj.options[i].selected=true;
    }
}

function selectacls(objnames){
    for (objname in objnames){
        obj = document.getElementById(objnames[objname]);
        for (i=0; i<obj.length; i++){
            obj.options[i].selected=true;
        }
    }
}

function changetype(doc){
    obj = doc.getElementById("mtype");
    t = obj.value;

    for(var i=0; i< obj.options.length; i++){
        o = doc.getElementById("div_"+obj.options[i].value);
        if (o){
            o.style.display = "none";
        }
    }
    if (doc.getElementById("div_"+obj.value)){
        doc.getElementById("div_"+obj.value).style.display = "block";
    }
}
