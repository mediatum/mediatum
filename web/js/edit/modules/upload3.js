/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function showOrHide(selector, selectedIndex){
    if (selectedIndex == 0) {
        $(selector).hide();
    }
    else {
        $(selector).show();
    }
}

function createMetaObject(){
    var ajax_response;
    var options = {
          url: '/edit/edit_content?action=createobject&func=createMetaObject&contenttype='+$('#schema').val().split('|')[1]+'&schema='+$('#schema').val().split('|')[0]+'&id='+id,
          async: false,
          dataType: 'json',
          success: function(data){
              ajax_response = data;
              $('#metaform').hide();
              document.location = '/edit/edit_content?srcnodeid='+id+'&id='+data.newid+'&func=createMetaObject&tab=metadata'
          }
        };

    $.ajax(options);
    updateNodeLabels("");
}

function disenableInput(index) {
  if (index != 0) {
    $("#input_identifier").prop('disabled', false);
    $('#identifier_subform').show();
  }
  else {
    $("#input_identifier").prop('disabled', true);
    $('#identifier_subform').hide();
  }
}
