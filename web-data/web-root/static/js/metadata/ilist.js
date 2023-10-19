/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

var old_id = new Array();
function trim(str) {
    return str.replace(/^\s*|\s*$/g,"");
}

function pick(value) {
    val = "";
    if (window.opener && !window.opener.closed) {
        el = document.getElementById('values');
        doc = window.opener.document;
        for(i=0; i< old_id.length;i++) {
            if(val.length) {
                val+= ";";
            }
            val += el.options[old_id[i]].value;
        }
        doc.getElementById(value).value=val;
    }
    window.close();
}

function getValue(value) {
    if (window.opener && !window.opener.closed) {
        doc = window.opener.document;
        arr = doc.getElementById(value);

        if (arr) {
            arr = arr.value.split(";");
            selObj = document.getElementById('values');
            for (i=0; i<selObj.length; i++) {
                for(j=0; j<arr.length; j++) {
                    if (trim(arr[j]) == selObj.options[i].value) {
                         old_id[j] = i;
                    }
                }
            }
            if (old_id.length>0) {
                for(i=0; i<old_id.length;i++){
                    selObj.options[old_id[i]].selected = true;
                }
            }
        } else {
            return;
        }
        setNumber();
    }
}

function setNumber() {
    c = 0;
    selObj = document.getElementById('values');

    x = new Array();
    found=false;
    for (i=0; i<selObj.length; i++) {
        if (selObj.options[i].selected) {
            x.push(i);
            found = false;
            for(j=0; j< old_id.length;j++) {
                if(old_id[j]==i){
                    found=true;
                }
            }
            //add element
            if (found==false) {
                old_id.push(i);
            }
        }
    }

    for (i=0; i<old_id.length; i++) {
        found = false;
        for(j=0; j<x.length; j++) {
            if(x[j]==old_id[i]) {
                found = true;
            }
        }
        //remove element
        if (found==false) {
            old_id.splice(i,1);
        }
    }

    for (i=0; i<selObj.length; i++) {
        if (selObj.options[i].selected) {
            c++;
        }
    }

    obj = document.getElementById('count');
    obj.firstChild.data = c;
}

function showValues() {
    txt = "";
    selObj = document.getElementById('values');

    for(i=0; i<old_id.length; i++) {
        txt += "- " + selObj.options[old_id[i]].value + "\n";
    }
    if (txt!="") {
        alert(txt);
    }
}

function clearSelection() {
    selObj = document.getElementById('values');
    for (i=0; i<selObj.length; i++) {
        selObj.options[i].selected = false;
    }
}
