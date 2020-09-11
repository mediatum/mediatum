/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function createObjectFromIdentifier(){

    var ajax_response;

    var options = {
          url: '/edit/edit_content?action=obj_from_identifier&func=createObjectFromIdentifier&identifier_importer='+$('#identifier_importer').val()+'&identifier='+$('#input_identifier').val()+'&id='+id,
          async: false,
          dataType: 'json',
          success: function(data){
              ajax_response = data;

              if (data.error != '') {
                var msg = data.error;
                if (data.error_detail != '') {
                msg = msg + '\n' + data.error_detail;
                }
                alert(msg);
              }
              else {
                $('#metaform').hide();
                updateNodeLabels("");
                if (false && typeof data.newid !== 'undefined') {
                  document.location = '/edit/edit_content?id='+data.newid+'&func=createObjectFromIdentifier&tab=metadata'  // open newly created node in metadata editor
                }
                else
                {
                  document.location = '/edit/edit_content?id='+id+'&func=createObjectFromIdentifier'; // show content of upload container
                }
              }
          }
        };
      $.ajax(options);
}
