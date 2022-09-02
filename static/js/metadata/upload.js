/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/
function getTargetNodeID() {

    var targetnodeid = "";

    try {
        // if this snippet is shown in a workflow-step editor
        targetnodeid = $('input[name=stepid]').val();
    } catch (err) {
        targetnodeid = "";
    }

    if (!targetnodeid) {
        try {
            // if this snippet is shown in a metadata editor
            var changeform = $("#changeform");
            var action_edit_content = changeform.attr("action");
            var metadata = changeform.children(':input[name="tab"]').val();
            var edit_id = changeform.children(':input[name="id"]').val();
            targetnodeid = edit_id;
        } catch(err) {}
    }
    return targetnodeid;
}

function whereAreWe() {

    var targetnodeid = "";
    var we_are_now = "";

    try {
        // if this snippet is shown in a workflow-step editor
        targetnodeid = $('input[name=stepid]').val();
    } catch(err) {
        targetnodeid = "";
    }

    if (targetnodeid) {
        we_are_now = "admin_workflow_step_editor";
    }

    if (!targetnodeid) {
        try {
            // if this snippet is shown in a metadata editor
            var changeform = $("#changeform");
            var action_edit_content = changeform.attr("action");
            var metadata = changeform.children(':input[name="tab"]').val();
            var edit_id = changeform.children(':input[name="id"]').val();
            targetnodeid = edit_id;
        } catch(err) {}

        if (targetnodeid) {
            we_are_now = "edit_metadata_editor";
        }
    }
    return we_are_now;
}

function questionDelName(name){
    if (name=="") {
        return confirm(unescape("Soll dieser Eintrag wirklich gel%F6scht werden?"));
    } else {
        return confirm(unescape("Soll der Eintrag '"+name+"' wirklich gel%F6scht werden?"));
    }
}

function m_upload_delete_file_json_for_targetnode(fieldname, filename) {

    if (!questionDelName(filename)) {
        return false;
    }

    var url = '/md_upload?jsoncallback=?';

    var options = {
        type: 'POST',
        cmd: 'delete_file',
        targetnodeid: getTargetNodeID(),
        m_upload_field_name: fieldname,
        prefixed_filename: filename,
    };
    $.getJSON(url, options, function(data) {
        var errors=data['errors'];
        if (errors) {
            $("#response_FOR_"+fieldname).html("");
            $.each(errors, function(index, value) {
                $("<div/>").html(value).attr('style', 'color:red').appendTo("#response_FOR_"+fieldname);
            });
        } else {
            $("#response_FOR_"+fieldname).html("");
        }

        var filelist=data['filelist'];
        if (filelist) {
            $("<div/>").html(data['html_filelist']).appendTo("#file_list_FOR_"+fieldname);
        }
    });

    setTimeout(function() {m_upload_load_file_list_json_for_targetnode(getTargetNodeID(), fieldname); }, 1000);
    return false;

}

function m_upload_load_file_list_json_for_targetnode(targetnodeid, fieldname) {

    var url = '/md_upload?jsoncallback=?';

    var options = {
        type: 'POST',
        cmd: 'list_files',
        targetnodeid: targetnodeid,
        m_upload_field_name: fieldname,
    };
    $.getJSON(url, options, function(data) {
        var filelist=data['filelist'];
        if (filelist) {
            $("#file_list_FOR_"+fieldname).html("");
            $("<div/>").html(data['html_filelist']).appendTo("#file_list_FOR_"+fieldname);
        }
    });
}

function m_upload_register_fieldname(fieldname) {
    $(document).ready(function () {
        var targetnodeid = getTargetNodeID();
        if (! targetnodeid=="") {
            $('input[name=targetnodeid_FOR_' + fieldname + ']').val(targetnodeid);
            $('input[name=upload_submit_FOR_' + fieldname + ']').val("Submit");
            $('div[name=upload_warn_div_FOR_' + fieldname + ']').hide();

            $('input[name=m_upload_file_FOR_' + fieldname + ']').removeAttr("disabled"); // type=file
            $('input[name=upload_submit_FOR_' + fieldname + ']').removeAttr("disabled"); // type=submit
            $('input[name=upload_submit_FOR_' + fieldname + ']').val("Submit");
            $('div[name=upload_warn_div_FOR_' + fieldname + ']').hide();

            m_upload_load_file_list_json_for_targetnode(targetnodeid, fieldname);
        } else {
            $('input[name=m_upload_file_FOR_' + fieldname + ']').attr("disabled","disabled"); // type=file
            $('input[name=upload_submit_FOR_' + fieldname + ']').attr("disabled","disabled"); // type=submit
            $('input[name=upload_submit_FOR_' + fieldname + ']').val("Submit (disabled)");
            $('div[name=upload_warn_div_FOR_' + fieldname + ']').show();
        }
    });
}

function m_upload_submit(fieldname) {

    $('#submitter_class_'+fieldname).val('m_upload');
    $('input[name=submitter_FOR_'+fieldname+']').val(fieldname);
    $('input[name=submitter]').val(fieldname);

    var we_are_now = whereAreWe();
    var current_form_id = '#addmfield';

    if (we_are_now == "admin_workflow_step_editor") {
        current_form_id = '#addmfield';
    } else if (we_are_now == "edit_metadata_editor") {
        current_form_id = '#myform';
    }

    var options = {
        url: '/md_upload',
        type: 'POST',
        success:   function(data) {
            var res = jQuery.parseJSON(data);

            $("#response_FOR_"+fieldname).html("");
            var errors = res['errors'];
            if (errors) {
                $.each(errors, function(index, value) {
                    $("<div/>").html(value).attr('style', 'color:red').appendTo("#response_FOR_"+fieldname);
                });
            }

            var copy_report = res['copy_report'];
            if (copy_report) {
                $("<div/>").html(copy_report).attr('style', 'color:blue').appendTo("#response_FOR_"+fieldname);
            }
        },
        error: function() { alert("error_FOR_"+fieldname); },
        complete: function() {
            $(current_form_id).unbind();
            m_upload_load_file_list_json_for_targetnode(getTargetNodeID(), fieldname);

            $('input[name=m_upload_file_FOR_'+fieldname+']').attr('value', '');
        },
    };
    var res = $(current_form_id).submit(function() {
        $(this).ajaxSubmit(options);
        return false;
    });

    return false;
}
