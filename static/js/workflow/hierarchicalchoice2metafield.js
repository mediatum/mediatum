/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/
$(document).ready(function () {
    $("button[name='gotrue']").attr('disabled', true);
    $("button[name='gotrue']").css('opacity', 0.5);
    $("#hierarchicalchoice2metafield").fancytree({
        icons: false,
        source: JSON.parse($('#fancytreesource').text()),
        activate: function(event, data) {
            if (data.node.hasChildren()) {
                $("#hierarchicalmetafield").val("");
                $("button[name='gotrue']").attr('disabled', true);
                $("button[name='gotrue']").css('opacity', 0.5);
            } else {
                $("#hierarchicalmetafield").val(data.node.key);
                $("button[name='gotrue']").attr('disabled', false);
                $("button[name='gotrue']").css('opacity', 1);
            }
        },
    });
});
