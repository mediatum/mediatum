/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

var allChecked = false;
$(document).ready(function() {
    $('.checkbox').attr('checked', false);

    $('.checkbox, .toggled_text').click(function() {
        if ($('.checkbox:checked').size() > 0) {
            $(':button').attr('disabled', false);
        } else {
            $(':button').attr('disabled', true);
        }
    });
});

function submit(id, csrf) {
    if ($('.checkbox:checked').size() > 0) {
        if ($("#selectid").val() == "delete") {
            confirmf(id, '#confirm_delete', csrf);
        } else {
            confirmf(id, '#confirm_move', csrf);
        }
    }
}

function confirmf(id, v, csrf) {
    if (confirm($(v).html())) {
        var selected = new Array();
        $('.checkbox:checked').each(function() {
            selected.push($(this).attr('id'));
        });

        $.ajax({
            url: '/mask?id='+id+'&action='+$('select').val(),
            traditional: true, //would POST param "obj[]" with brackets in the name otherwise
            data: {obj: selected, csrf_token: csrf},
            type: 'POST',
            success: function (response) {
                $('#workflow').replaceWith($(response).find('#workflow'));
            },
        });
    }
}

function toggleAll() {
    $('.toggled_text').toggle();
    if (allChecked == true) {
        $('.checkbox').each(function() {
            $(this).prop('checked', false);
        });
        allChecked = false;
    } else {
        $('.checkbox').each(function() {
            $(this).prop('checked', true);
        });
        allChecked = true;
    }
}


// inspired by https://stackoverflow.com/questions/374644/how-do-i-capture-response-of-form-submit
document.getElementById('mediatum-workflow-editmetadata-form').addEventListener('submit', (event) => {
    if (event.submitter.name == "gofalse")
        return;
    event.preventDefault();
    fetch(event.target.action, {
        method: 'POST',
        body: new FormData(event.target) // event.target is the form
    }).then((response) => {
        if (!response.ok) {
            alert(`HTTP error! Status: ${response.status}`);
            return;
        }
        return response.text();
    }).then((body) => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(body, "text/html");
        fielderrors = doc.getElementById("mediatum-workflow-editmetadata-fielderrors");
        key = doc.getElementById("mediatum-workflow-editmetadata-submitkey");
        if (key != null) {
            key = key.innerText;
            form = document.getElementById("mediatum-workflow-editmetadata-key");
            document.getElementsByName("mediatum-workflow-editmetadata-keyinput")[0].value = key;
            form.submit();
            return;
        }
        mediatum_metadataeditor_highlighterrors(JSON.parse(fielderrors.innerText));
    }).catch((error) => {
        alert(error);
    });
});
