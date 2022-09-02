/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

$(document).ready(function()
    $('input[type="submit"]').click(function() {
        var submit_form = confirm($('#confirm_popup').html());
        return submit_form;
    });
});
