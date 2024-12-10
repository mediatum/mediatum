/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

var firstload = 1;
function getSelect(id) {
    if (firstload==1){
        var span = document.createElement("span");
        span.classList.add("mediatum-editor-nav-image-wait");
        document.getElementById("useracl").replaceChildren(span);
        getEditPage('useracl', id, 'acls', 'get_userlist');
        firstload=0;
    }
}

// load data to tab via ajax
function get_json_for_action(src, action, id) {
  var span = document.createElement("span");
  span.classList.add("mediatum-editor-nav-image-wait");
  var tempdiv = document.createElement("span");
  tempdiv.id = "tempdiv";
  tempdiv.appendChild(span);
  $(src).append(tempdiv);
  var ajax_response;

  var options = {
        url: '/edit/edit_content?tab=acls&action='+action+'&style=popup&id='+id, // id instead of ids
        async: false,
        dataType: 'json',
        success: function (response) {
            ajax_response = response;
            $('#tempdiv').remove();
            console.log('edit_action_sync: $.ajax returns: ', response);
            console.dir(response);

        }
      };

  $.ajax(options);
}


// http://stackoverflow.com/questions/1447728/how-to-dynamic-filter-options-of-select-with-jquery

jQuery.fn.filterByText = function(textbox) {
    return this.each(function() {
        var select = this;
        var options = [];
        $(select).find('option').each(function() {
            options.push({value: $(this).val(), text: $(this).text(), title: $(this).attr('title')});
        });
        $(select).data('options', options);

        $(textbox).bind('change keyup', function() {
            var options = $(select).empty().data('options');
            var search = $.trim($(this).val());
            var regex = new RegExp(search,"gi");

            $.each(options, function(i) {
                var option = options[i];
                if(option.text.match(regex) !== null) {
                    $(select).append(
                        $('<option>').text(option.text).val(option.value).attr('title', option.title)
                    );
                }
            });
        });
    });
};

$(document).ready(function () {
    sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content"},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0},
        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed
    });
});

$(function() {
    $('#select_right_acl_read').filterByText($('#input_acl_read'));
});

$(function() {
    $('#select_right_acl_write').filterByText($('#input_acl_write'));
});

$(function() {
    $('#select_right_acl_data').filterByText($('#input_acl_data'));
});

$(function() {
    $('#select_right_user_read').filterByText($('#input_user_read'));
});

$(function() {
    $('#select_right_user_write').filterByText($('#input_user_write'));
});

$(function() {
    $('#select_right_user_data').filterByText($('#input_user_data'));
});
