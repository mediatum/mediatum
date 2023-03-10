/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function openPopup(url, name, width, height){
    var win1 = window.open(url,name,'width='+width+',height='+height+',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=no');
    win1.focus();
    return win1;
}

function onNewVersionChecked (self) {
    if (self.checked) {
        $('#version_comment').show();
        $('#version_comment textarea').attr('required', '');
        $('#save_button').prop('disabled', false);
    } else {
        $('#version_comment').hide();
        $('#version_comment textarea').removeAttr('required');
        $('#save_button').prop('disabled', true);
    }
}
