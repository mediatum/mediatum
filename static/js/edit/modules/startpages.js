/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

var CKEDITOR_BASEPATH = '/ckeditor/';

function questionDel(filename){ //old
    yes = confirm(unescape(document.getElementById("deleteconfirm").innerHTML));
    if (!yes) return;

    csrf = csrf.replace("##", "!!!!!");
    $.ajax({
        url: '/edit/edit_content?id='+id+'&tab=startpages',
        async: false,
        type: 'POST',
        data : { delete_: filename, csrf_token: csrf},
        success: function (response) {
           document.getElementById("filetable").tBodies[0].innerHTML = response;
        },
        error: function (msg) {
            alert("error: " + msg.toSource());
        }
    });
}

function editFile(filename){ // edit file click
    $("#filename").val(filename);
    $.getJSON('/edit/edit_content?id='+id+'&tab=startpages&action=getfile&filename='+filename, function(data) {
        CKEDITOR.instances['page_content'].setData(data.filecontent);
        $('#editform').css('display','block');
        parent.$('#overlay').css('display', 'block');
        CKEDITOR.instances['page_content'].resize('100%', $('#editform-form').height());
    });
}

function addFile(){ // create new file
    $("#filename").val('add');
    CKEDITOR.instances['page_content'].setData('');
    $('#editform').css('display','block');
    parent.$('#overlay').css('display', 'block');
    CKEDITOR.instances['page_content'].resize('100%', $('#editform-form').height());
}

function closeForm(){ // close form
    $('#editform').css('display','none');
}

function handleCKEditorPost(){ // save data
    csrf = csrf.replace("##", "!!!!!");
    $.ajax({ type :"post",
        data : { data: CKEDITOR.instances['page_content'].getData(), csrf_token: csrf },
        url : '/edit/edit_content?id='+id+'&tab=startpages&action=save&filename='+$("#filename").val()
    }).done(function(ret){
        $('#editform').css('display','none');
        document.getElementById("filetable").tBodies[0].innerHTML = ret;
    });
}

function SelectFile( fileUrl ){
    // Helper function to get parameters from the query string.
    function getUrlParam(paramName){
      var reParam = new RegExp('(?:[\?&]|&amp;)' + paramName + '=([^&]+)', 'i') ;
      var match = window.location.search.match(reParam) ;
      return (match && match.length > 1) ? match[1] : '' ;
    }
    var funcNum = getUrlParam('CKEditorFuncNum');
    window.opener.CKEDITOR.tools.callFunction(funcNum, fileUrl);
    window.close() ;
}

function delete_nodefile(obj){
    o = $(obj);
    if(confirm($('#deleteconfirm').html())){
        $.get('/edit/edit_content/'+id+'/startpages/'+o.attr('name')+'?delete=True', function(data) {});
        o.parent().parent().remove();
        if(($('#files').children().length)==0){
            $('#nofiles').show();
        }
    }
}

function ckeditor_config() {
    var ckeditor = CKEDITOR.replace('page_content');
    ckeditor.config.filebrowserBrowseUrl = '/edit/edit_content?id='+id+'&'+'tab=startpages'+'&'+'option=filebrowser';
    ckeditor.config.filebrowserUploadUrl = '/edit/edit_content?id='+id+'&'+'tab=startpages'+'&'+'option=filebrowser';
    ckeditor.config.filebrowserImageUploadUrl = '/edit/edit_content?id='+id+'&'+'tab=startpages'+'&'+'option=htmlupload';
    ckeditor.config.filebrowserImageBrowserUrl = '/edit/edit_content?id='+id+'&'+'tab=startpages'+'&'+'option=filebrowser';
    ckeditor.config.filebrowserWindowWidth = '500';
    ckeditor.config.filebrowserWindowHeight= '500';
    ckeditor.config.allowedContent = true;
    ckeditor.config.height = '100%';
    ckeditor.config.toolbar = 'Full';
    ckeditor.config.toolbar_Full = [
            ['Source', 'Save', 'cancel', 'Preview'],
            ['Cut','Copy','Paste','PasteText','PasteFromWord','-', 'SpellChecker', 'Scayt'],
            ['Undo','Redo','-','Find','Replace','-','SelectAll','RemoveFormat'],
            '/',
            ['Bold','Italic','Underline','Strike','-','Subscript','Superscript'],
            ['JustifyLeft','JustifyCenter','JustifyRight','JustifyBlock'],
            ['NumberedList','BulletedList','-','Outdent','Indent','Blockquote','CreateDiv', 'Image'],
            ['Link','Unlink','Anchor','Table','HorizontalRule','Smiley','SpecialChar'],
            '/',
            ['Styles','Format','Font','FontSize','TextColor','BGColor','ShowBlocks']
        ];
}

$(document).ready(function () {
    var sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content", onresize: $.layout.callbacks.resizePaneAccordions},
        north:{paneSelector: "#navigation_content", size:40,resizable:false,closable:false},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0},
        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed
    });
    $("#accordion").accordion({heightStyle: "fill"});
});
