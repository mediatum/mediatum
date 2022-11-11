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

function submit(csrf) {
    if ($('.checkbox:checked').size() > 0) {
        if ($("#selectid").val() == "delete") {
            confirmf('#confirm_delete', csrf);
        } else {
            confirmf('#confirm_move', csrf);
        }
    }
}

function confirmf(v, csrf) {
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
