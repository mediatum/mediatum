/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function openPopup(url, name, width, height){
    var win1 = window.open(url,name,'width='+width+',height='+height+',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=no');
    win1.focus();
    return win1;
}

function handle_multiedit_checkbox(name){
    nodefield_value_array = document.getElementById(`mediatum-editor-nodefield-byname-${name}`).getElementsByClassName("mediatum-editor-nodefield-value");

    if (nodefield_value_array.length !== 1) {
        throw new RangeError(`Array length is ${nodefield_value.length}, expected 1`);
    }

    nodefield_value_array[0].disabled = ! document.getElementById(`mediatum-editor-nodefield-multiedit-${name}`).checked;
}

$(document).ready(function () {
    sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content",},
        north:{paneSelector: "#navigation_content", size:130,resizable:false,},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0,},

        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed,

    });
    var k = parent.last_activated_node.key;
    updateNodeLabels(k);
});

// inspired by https://stackoverflow.com/questions/374644/how-do-i-capture-response-of-form-submit
document.getElementById('mediatum-edit-form-metadata').addEventListener('submit', (event) => {
    event.preventDefault();
    fetch(event.target.action, {
        method: 'POST',
        body: new URLSearchParams(new FormData(event.target)) // event.target is the form
    }).then((response) => {
        if (!response.ok) {
            alert(`HTTP error! Status: ${response.status}`);
            return;
        }
        return response.json();
    }).then((body) => {
        console.log(body);
        if (Object.keys(body) != 0) {
            mediatum_metadataeditor_highlighterrors(body);
            return;
        }
        const url = new URL(location.href);
        url.searchParams.delete("tab");
        for (const param of ['id', 'srcnodeid']) {
            if (url.searchParams.get(param) == null) {
                url.searchParams.append(param, document.getElementsByName(param)[0].value.split(',')[0]);
            }
        }
        document.location.href = url.href;
        return;
    }).catch((error) => {
        alert(error);
    });
});
