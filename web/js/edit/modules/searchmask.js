/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function change_searchtype(){
    var ajax_response;
    var options = {
          url: '/edit/edit_content?id='+id+'&tab=searchmask'+'&searchtype='+$('#searchtype_id').val()+'&isnewfield='+'&searchtypechanged=true',
          async: false,
          dataType: 'json',
          success: function(data){
              ajax_response = data;
              $('#fbody').html(data.content);
          }
        };
    $.ajax(options);
}

function select_schema(fid){
    var ajax_response;
    var options = {
          url: '/edit/edit_content?id='+id+'&tab=searchmask'+'&searchtype=own'+'&schema='+$('#ssel').val()+'&isnewfield='+'&selectedfield='+fid+'&fieldname='+$('#fnid').val(),
          async: false,
          dataType: 'json',
          success: function(data){
              ajax_response = data;
              $('#fbody').html(data.content);
          }
        };
    $.ajax(options);
}

function create_subfield(fid){
    var ajax_response;
    var options = {
          url: '/edit/edit_content?id='+id+'&tab=searchmask'+'&searchtype=own'+'&schema='+$('#ssel').val()+'&schemafield='+$('#sfsel').val()+'&isnewfield='+'&selectedfield='+fid+'&fieldname='+$('#fnid').val()+'&createsub=',
          async: false,
          dataType: 'json',
          success: function(data){
              ajax_response = data;
              $('#fbody').html(data.content);
          }
        };
    $.ajax(options);
}

function delete_subfield(sfid, fid){
    var ajax_response;
    var options = {
          url: '/edit/edit_content?id='+id+'&tab=searchmask'+'&searchtype=own'+'&delsub_'+sfid+'.x='+'&delsub_'+sfid+'.y='+'&isnewfield='+'&selectedfield='+fid+'&schema='+'&fieldname='+$('#fnid').val(),
          async: false,
          dataType: 'json',
          success: function(data){
              ajax_response = data;
              $('#fbody').html(data.content);
          }
        };
    $.ajax(options);
}

function delete_field(fid){
    var ajax_response;
    var options = {
          url: '/edit/edit_content?id='+id+'&tab=searchmask'+'&searchtype=own'+'&del_'+fid+'.x='+'&del_'+fid+'.y='+'&isnewfield='+'&selectedfield='+fid+'&schema='+'&fieldname='+$('#fnid').val(),
          async: false,
          dataType: 'json',
          success: function(data){
              ajax_response = data;
              $('#fbody').html(data.content);
          }
        };
    $.ajax(options);
}

function close_field(fid){
    var ajax_response;
    var options = {
          url: '/edit/edit_content?id='+id+'&tab=searchmask'+'&searchtype=own'+'&close.x='+'&close.y='+'&isnewfield='+'&selectedfield='+fid+'&schema='+'&fieldname='+$('#fnid').val(),
          async: false,
          dataType: 'json',
          success: function(data){
              ajax_response = data;
              $('#fbody').html(data.content);
          }
        };
    $.ajax(options);
}

function create_field(){
    var ajax_response;
    var options = {
          url: '/edit/edit_content?id='+id+'&tab=searchmask'+'&searchtype=own'+'&isnewfield=yes',
          async: false,
          dataType: 'json',
          success: function(data){
              ajax_response = data;
              $('#fbody').html(data.content);
          }
        };
    $.ajax(options);
}

function open_field(fid){
    var ajax_response;
    var options = {
          url: '/edit/edit_content?id='+id+'&tab=searchmask'+'&searchtype=own'+'&open_'+fid+'.x='+'&open_'+fid+'.y='+'&isnewfield=',
          async: false,
          dataType: 'json',
          success: function(data){
              ajax_response = data;
              $('#fbody').html(data.content);
          }
        };
    $.ajax(options);
}

$(document).ready(function () { // set correct height of scrollable content
   var sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content", onresize: $.layout.callbacks.resizePaneAccordions},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0}
   });
});
