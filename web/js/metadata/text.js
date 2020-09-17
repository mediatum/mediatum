/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function detail(value, title) {
    o = document.getElementById("spcvalue");
    o.innerHTML = String.fromCharCode(value)
    o = document.getElementById("spcname");
    o.innerHTML = title;
}

function setFormated(obj){
    o = document.getElementById("formatedvalue");
    o.innerHTML = obj.value;
}

function insert(aTag, eTag) {
    if (eTag=='') {
        aTag = String.fromCharCode(aTag);
    }
    var input = document.getElementById("value");
    input.focus();
    if (typeof document.selection != 'undefined') {
        var range = document.selection.createRange();
        var insText = range.text;
        range.text = aTag + insText + eTag;
        range = document.selection.createRange();
        if (insText.length == 0) {
            range.move('character', -eTag.length);
        } else {
            range.moveStart('character', aTag.length + insText.length + eTag.length);
        }
        range.select();
    } else if (typeof input.selectionStart != 'undefined') {
        var start = input.selectionStart;
        var end = input.selectionEnd;
        var insText = input.value.substring(start, end);
        input.value = input.value.substr(0, start) + aTag + insText + eTag + input.value.substr(end);

        var pos;
        if (insText.length == 0) {
            pos = start + aTag.length;
        } else {
            pos = start + aTag.length + insText.length + eTag.length;
        }
        input.selectionStart = pos;
        input.selectionEnd = pos;
    } else {
        var pos;
        var re = new RegExp('^[0-9]{0,3}$');
        while (!re.test(pos)) {
            pos = prompt("insert at (0.." + input.value.length + "):", "0");
        }
        if (pos > input.value.length) {
            pos = input.value.length;
        }
        var insText = prompt("insert text to format:");
        input.value = input.value.substr(0, pos) + aTag + insText + eTag + input.value.substr(pos);
    }
    setFormated(input);
}

function init(name) {
    o = document.getElementById('value');
    if (window.opener && !window.opener.closed) {
        o.value = window.opener.document.getElementById(name).value;
    }
    o.focus();
    setFormated(o);
}

function save(value) {
    if (window.opener && !window.opener.closed) {
        window.opener.document.getElementById(value).value=document.getElementById('value').value;
    }
    window.close();
}
