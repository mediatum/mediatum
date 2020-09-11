/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function openMetaForm(){
    var ajax_response;
    var options = {
        url: '/edit/edit_content?action=addmeta&func=openMetaForm&id='+id,
        async: false,
        dataType: 'json',
        success: function(data){
            ajax_response = data;
            $('#metaformcontent').html(data.content);
            $('<input>').attr({
                type: 'hidden',
                name: 'srcnodeid',
                value: id,
            }).appendTo($('#metaformcontent'));
            $('#metaform').show();
        }
    };

    $.ajax(options);
    parent.$('#overlay').css('display', 'block');
}

function closeMetaForm(){ // close upload form
    $('#metaform').hide();
}

function openDoiForm(){
    var ajax_response;
    var options = {
        url: '/edit/edit_content?action=adddoi&func=openMetaForm&id='+id,
        async: false,
        dataType: 'json',
        success: function(data){
            ajax_response = data;
            $('#metaformcontent').html(data.content);
            $('#metaform').show();
        }
    };
    $.ajax(options);
}

function closeDoiForm(){ // close upload form
    $('#metaform').hide();
}

var number_files = 0;
var all_files = 0;
var err_files = 0;
var singlefile = 0;

function loadEditArea02(id){
    $('.ui-layout-center').attr('src', '/edit/edit_content?id='+id);
}

var uploaderfile = null;
var uploaderbibtext = null;

function openUploadFormPluploadWidgetFile(){ // show upload form
    var ajax_response;
    var options = {
        url: '/edit/edit_content?action=removefiles&func=openUploadFormPluploadWidgetFile&id='+id,
        async: false,
        dataType: 'json',
        success: function(data) {
            ajax_response = data;
            if (data.state=='error'){
                console.log('upload.html: openUploadFormPluploadWidgetFile: error removing files');
            }
            else {
                console.log('upload.html: openUploadFormPluploadWidgetFile:' + JSON.stringify(data));
            }
        }
    };

    $.ajax(options);

    uploaderfile = init_plupload_widget_file();

    uf = $('#mediatum_uploadform_plupload_widget_file');
    uf.show();

    hc = $('div.plupload_header');
    ufs = $('#uploaderfile_filelist');
    var x = $('#uploaderfile_dropbox');
    var uc = $('#uploader_container');
    hc.remove();
    parent.$('#overlay').css('display', 'block');
}

function closeFormPluploadWidgetFile() { // close upload form
    $('#mediatum_uploadform_plupload_widget_file').hide();
        parent.$('#overlay').css('display', 'none');

    // make sure, the plupload widget is reinitialized
    return reloadPage(id);
}

function createObjectsPluploadFile(){ // build object out of files
    console.group('edit.modules: upload.html createObjectsPluploadFile');

    $('#uploader_start').attr('aria-disabled','true');  // not functional ?

    number_files = all_files = $('#uploaderfile_filelist').children().length;
    if (number_files==1){
        singlefile==1;
}

console.log('number_files: ' + number_files + ' all_files: ' + all_files);

var new_elem = $('<img height="30" src="/img/wait.gif" />');
new_elem.insertBefore('#span_plupload_createobjects_file');
new_elem.insertBefore('.plupload_logo');
$('.plupload_logo').attr('class', '');

var htree = parent.gethometree();

$.each($(".typesel"), function(i, l){
    x = $(l);
    value = x.val(); // value
    type = x.attr('id'); // type
    files = x.parents().children('#'+x.attr('id')+':last').val(); //files

    console.log('upload.createObjectsfile: l:'+l+', value:'+value+', type:'+type+', files:'+files);

    var ajax_response;

    var options = {
        url: '/edit/edit_content?action=buildnode&func=createObjectsPlupload&id='+id+'&files='+encodeURIComponent(files)+'&type='+type+'&value='+value,
        async: false,
        dataType: 'json',
        success: function (data) {
            ajax_response = data;
            console.log('createObjects');
            curr_file = $('#uploaderfile_filelist').children().slice(all_files-number_files).first()
            var err = 0;
            if (data.errornodes.length>0){
                err_div = curr_file[0].children[1].children[2];
                for (i = 0; i < data.errornodes.length; i ++) {
                  if (err_div.id == 'err_' + data.errornodes[i][2]) {
                    err_div.textContent = data.errornodes[i][1];
                    err = 1;
                    break;
                  }
                }
            }
            if (data.errornodes.length>0 && err != 0){
                err_files += 1;
                $('#uploaderfile_filelist').children().slice(all_files-number_files).first().removeClass('blue');
                $('#uploaderfile_filelist').children().slice(all_files-number_files).first().addClass('red');
            }else{

                $('#uploaderfile_filelist').children().slice(all_files-number_files).first().remove();

                $('#divStatus').html('processing / ' + number_files);
                data.new_tree_labels.forEach(
                function(nentry) {
                    console.log('tree_node: '+nentry.id+', new label: '+nentry.label);
                    changed_node = htree.getNodeByKey(nentry.id);
                    changed_node.title = nentry.label;
                    changed_node.renderTitle();
                }
                )
              all_files -= 1;
            }
            number_files -= 1;

            console.log('$.ajax returns: '+data);
            console.log('number_files: ' + number_files);
        }, // success function
    }; // options

    $.ajax(options);

    var childnode = ajax_response;

}) // $.each
if (err_files == 0) {
  console.log('going to call closeFormFile()');
  closeFormPluploadWidgetFile();
  console.log('after called: closeFormFile()');
  console.log('going to call loadEditArea(id), id:'+id);
  parent.loadEditArea(id);
  console.log('after called loadEditArea(id), id:'+id);
} else {
  // $('#error_dummy')[0].textContent='';
  // throw "some files cannot be created";
  $('#id_button_createobjectsplupload_file').prop('disabled', true);
  $('#uploaderfile_browse').addClass('ui-state-disabled').attr('aria-disabled', 'true');
  new_elem[0].style.visibility = 'hidden';
}
console.groupEnd('edit.modules: upload.html createObjectsPluploadFile');
}  // function createObjectsPluploadFile

var files_uploaded_file = 0;

function init_plupload_widget_file() {
    csrf = csrf.replace("##", "!!!!!");
    var u = $(function() {

        /* NOT WORKING IN FIREFOX */
        moxie.core.utils.Mime.addMimeType("image/jpeg,jpg jpeg");
        moxie.core.utils.Mime.addMimeType("image/gif,gif");
        moxie.core.utils.Mime.addMimeType("image/png,png");
        moxie.core.utils.Mime.addMimeType("image/tiff,tiff");
        moxie.core.utils.Mime.addMimeType("image/svg+xml,svg");
        moxie.core.utils.Mime.addMimeType("image/bmp,bmp");
        moxie.core.utils.Mime.addMimeType("application/zip,zip");
        moxie.core.utils.Mime.addMimeType("application/pdf,pdf");
        moxie.core.utils.Mime.addMimeType("video/mp4,mp4");
        moxie.core.utils.Mime.addMimeType("audio/mpeg,mp3");

        $("#uploaderfile").plupload({
        // General settings
        runtimes : 'html5,silverlight,flash,html4',
        autostart: false,
        url : '/edit/edit_content?action=upload&func=init_plupload_widget_file&uploader=plupload&id='+id,
        // User can upload no more then 20 files in one go (sets multiple_queues to false)
        max_file_count: 0,  // default is 0 -> no limit
        //multipart_params : mpv,
        filters : {
            // Maximum file size
            //max_file_size : '1000mb',
            // Specify what files to browse for
            mime_types: [
            {title : "Image files", extensions : "jpg,jpeg,gif,png,tif,tiff,svg,bmp"},
            {title : "Zip files", extensions : "zip"},
            {title : "pdf files", extensions : "pdf"},
            {title : "mp4 video files", extensions : "mp4"},
            {title : "mp3 files", extensions : "mp3"},
            ]
        },
        // Rename files by clicking on their titles
        rename: true,
        // Sort files
        sortable: false,
        // Enable ability to drag'n'drop files onto the widget (currently only HTML5 supports that)
        dragdrop: true,
        // Views to activate
        views: {
            list: true,
            thumbs: false, // deactivate thumbs view
            active: 'list',
            remember: false,
        },
        // buttons to activate
        buttons: {
            browse: true,
            start: true,
            stop: true
        },
        // Flash settings
        flash_swf_url : '/js/plupload/Moxie.swf',
        // Silverlight settings
        silverlight_xap_url : '/js/plupload/Moxie.xap',
        // PreInit events, bound before any internal events
        preinit : {
            Init: function(up, info) {
                log('[Init]', 'Info:', info, 'Features:', up.features);
            },
            UploadFile: function(up, file) {
                log('[UploadFile]', file);
                // You can override settings before the file is uploaded
                // up.setOption('url', 'upload.php?id=' + file.id);
                // up.setOption('multipart_params', {param1 : 'value1', param2 : 'value2'});
                up.setOption('multipart_params', {csrf_token : csrf});
            }
        },
        // Post init events, bound after the internal events
        init : {
            PostInit: function(up) {
                // Called after initialization is finished and internal event handlers bound
                log('[PostInit]');
                files_uploaded = 0;
            },
            Browse: function(up) {
                // Called when file picker is clicked
                log('[Browse]');
            },
            Refresh: function(up) {
                // Called when the position or dimensions of the picker change
                log('[Refresh]');
            },
            StateChanged: function(up) {
                // Called when the state of the queue is changed
                log('[StateChanged]', up.state == plupload.STARTED ? "STARTED" : "STOPPED");
            },
            QueueChanged: function(up) {
                // Called when queue is changed by adding or removing files
                log('[QueueChanged]');
            },
            OptionChanged: function(up, name, value, oldValue) {
                // Called when one of the configuration options is changed
                log('[OptionChanged]', 'Option Name: ', name, 'Value: ', value, 'Old Value: ', oldValue);
            },
            BeforeUpload: function(up, file) {
                // Called right before the upload for a given file starts, can be used to cancel it if required
                log('[BeforeUpload]', 'File: ', file);

                var iframe_c = $("iframe.ui-layout-center");
                var fid = file.id;
                console.log('fid='+fid);
                var filelist_line = $("#"+fid);
                var c1 = filelist_line.children()[1];

                // sending additional parameters
                this.settings.multipart_params = {
                    "file_name" : file.name,
                    "data_extra" : $('#select_extra_' + fid).val()
                };
            },
            UploadProgress: function(up, file) {
                // Called while file is being uploaded
                log('[UploadProgress]', 'File:', file, "Total:", up.total);
            },
            FileFiltered: function(up, file) {
                // Called when file successfully files all the filters
                log('[FileFiltered]', 'File:', file);
            },
            FilesAdded: function(up, files) {
                // Called when files are added to queue
                log('[FilesAdded]');
                plupload.each(files, function(file) {
                    log('  File:', file);
                    //file.x = '777';
                    var iframe_c = $("iframe.ui-layout-center");
                    var fid = file.id;
                    console.log('fid='+fid);
                    var filelist_line = $("#"+fid);
                    console.log('filelist_line', filelist_line);

                    filelist_line.attr('class', 'progressContainer green');
                    var c1 = filelist_line.children()[1];
                    filename = file.name;
                    file_ext = filename.split('.').pop().toLowerCase();
                    var sel = '';
                    if (file_ext == 'bib') {
                        var sel = " <select name='tofiletype' class='select_unpack' id='select_extra_" + fid + "'>" +
                            "<option value='tofile'>" + js_upload_no_unpack + "</option>" +
                            "<option value='totype' selected>" + js_upload_unpack + "</option>" +
                        "</select>";
                    }

                    c1.innerHTML = c1.innerHTML + sel;
                    c1ppp = c1.parentNode.parentNode.parentNode;
                    c1ppp.style.position = 'relative';
                    c1ppp.style.top = '0px';
                    c1ppp.style.overflow = 'auto';
                });
            },
            FilesRemoved: function(up, files) {
                // Called when files are removed from queue
                log('[FilesRemoved]');
                plupload.each(files, function(file) {
                    log('  File:', file);
                });
            },
            FileUploaded: function(up, file, info) {
                // Called when file has finished uploading
                log('[FileUploaded] File:', file, "Info:", info);
                var iframe_c = $("iframe.ui-layout-center");
                var fid = file.id;
                console.log('fid='+fid);
                var filelist_line = $("#"+fid);
                console.log('filelist_line', filelist_line);
                filelist_line.attr('class', 'progressContainer blue');
                var c1 = filelist_line.children()[1];
                c1.innerHTML = c1.innerHTML + JSON.parse(info.response).ret;
                c1ppp = c1.parentNode.parentNode.parentNode;
                c1ppp.style.position = 'relative';
                c1ppp.style.top = '0px';
                c1ppp.style.overflow = 'auto';
                $('#select_extra_' + fid).hide();

                htree = parent.gethometree();
                JSON.parse(info.response).new_tree_labels.forEach(
                    function(nentry) {
                    console.log('tree_node: '+nentry.id+', new label: '+nentry.label);
                    changed_node = htree.getNodeByKey(nentry.id);
                    changed_node.data.title = nentry.label;
                    changed_node.render();
                    }
                );

                uc = $('#mediatum_uploader_container');
                x = uc.find('.ui-resizable-handle');
                x.remove();

                files_uploaded_file = files_uploaded_file + 1;
            },
            ChunkUploaded: function(up, file, info) {
                // Called when file chunk has finished uploading
                log('[ChunkUploaded] File:', file, "Info:", info);
            },
            UploadComplete: function(up, files) {
                // Called when all files are either uploaded or failed
                log('[UploadComplete]');
                if (files_uploaded_file > 0) {
                    $('#id_button_createobjectsplupload_file').prop('disabled', false);
                }
            },
            Destroy: function(up) {
                // Called when uploaderfile is destroyed
                log('[Destroy] ');
            },
            Error: function(up, args) {
                // Called when error occurs
                log('[Error] ', args);
                alert(args.message + ': ' + args.file.name);
            }
        }
    });
    });
    return u;
}

function openUploadFormPluploadWidgetBib(){ // show upload form
    var ajax_response;

    var options = {
        url: '/edit/edit_content?action=removefiles&func=openUploadFormPluploadWidgetBib&id='+id,
        async: false,
        dataType: 'json',
        success: function(data) {
            ajax_response = data;
            if (data.state=='error'){
                console.log('upload.html: openUploadFormPluploadWidgetBib: error removing files');
            }
            else {
                console.log('upload.html: openUploadFormPluploadWidgetBib:' + JSON.stringify(data));
            }
        }
    };

    $.ajax(options);

    uploaderbib = init_plupload_widget_bib();

    uf = $('#mediatum_uploadform_plupload_widget_bib');
    uf.show();

    hc = $('div.plupload_header');
    ufs = $('#uploaderbib_filelist');
    var x = $('#uploaderbib_dropbox');
    var uc = $('#uploader_container');
    hc.remove();
    parent.$('#overlay').css('display', 'block');
}

function closeFormPluploadWidgetBib() { // close upload form
    $('#mediatum_uploadform_plupload_widget_bib').hide();
        parent.$('#overlay').css('display', 'none');

    // make sure, the plupload widget is reinitialized
    return reloadPage(id);
}

function createObjectsPluploadBib(){ // build object out of files
    console.group('edit.modules: upload.html createObjectsPluploadBib');

    $('#uploader_start').attr('aria-disabled','true');  // not functional ?

    number_files = $('#uploaderbib_filelist').children().length;
    if (number_files==1){
        singlefile==1;
    }

    console.log('number_files: ' + number_files);

    var new_elem = $('<img height="30" src="/img/wait.gif" />');
    new_elem.insertBefore('#span_plupload_createobjects_bib');
    new_elem.insertBefore('.plupload_logo');
    $('.plupload_logo').attr('class', '');
    var htree = parent.gethometree();
    $.each($(".typesel"), function(i, l){
        x = $(l);
        value = x.val(); // value
        type = x.attr('id'); // type
        files = x.parents().children('#'+x.attr('id')+':last').val(); //files
        console.log('upload.createObjectsbib: l:'+l+', value:'+value+', type:'+type+', files:'+files);
        var ajax_response;
        var options = {
                url: '/edit/edit_content?action=buildnode&func=createObjectsPlupload&id='+id+'&files='+encodeURIComponent(files)+'&type='+type+'&value='+value,
                async: false,
                dataType: 'json',
                success: function (data) {
                    ajax_response = data;
                    console.log('createObjects');
                    if (data.errornodes.length>0){
                        $('#uploaderbib_filelist').children().first().removeClass('blue');
                        $('#uploaderbib_filelist').children().first().addClass('red');
                    }else{
                        number_files -= 1;

                        $('#uploaderbib_filelist').children().first().remove();

                        $('#divStatus').html('processing / ' + number_files);
                        data.new_tree_labels.forEach(
                        function(nentry) {
                            console.log('tree_node: '+nentry.id+', new label: '+nentry.label);
                            changed_node = htree.getNodeByKey(nentry.id);
                            changed_node.title = nentry.label;
                            changed_node.renderTitle();
                        }
                        )
                    }
                    console.log('$.ajax returns: '+data);
                    console.log('number_files: ' + number_files);
            }, // success function
        }; // options

        $.ajax(options);
        var childnode = ajax_response;
    }) // $.each
    console.log('going to call closeFormBib()');
    closeFormPluploadWidgetFile();
    console.log('after called: closeFormBib()');
    console.log('going to call loadEditArea(id), id:'+id);
    parent.loadEditArea(id);
    console.log('after called loadEditArea(id), id:'+id);
    console.groupEnd('edit.modules: upload.html createObjectsPluploadBib');
}  // function createObjectsPluploadBib

var files_uploaded_bib = 0;

function init_plupload_widget_bib() {
    csrf = csrf.replace("##", "!!!!!");
    var u = $(function() {
        moxie.core.utils.Mime.addMimeType("text/x-bibtex,bib");
        $("#uploaderbib").plupload({
            // General settings
            runtimes : 'html5,flash,silverlight,html4',
            autostart: false,
            url : '/edit/edit_content?action=upload&func=init_plupload_widget_bib&uploader=plupload&id='+id,
            // User can upload no more then 20 files in one go (sets multiple_queues to false)
            max_file_count: 0,  // default is 0 -> no limit
            //multipart_params : mpv,
            filters : {
                // Maximum file size
                //max_file_size : '1000mb',
                // Specify what files to browse for
                mime_types: [
                {title : "bibtex files", extensions : "bib"}
                ]
            },
            // Rename files by clicking on their titles
            rename: true,
            // Sort files
            sortable: false,
            // Enable ability to drag'n'drop files onto the widget (currently only HTML5 supports that)
            dragdrop: true,
            // Views to activate
            views: {
                list: true,
                thumbs: false, // deactivate thumbs view
                active: 'list',
                remember: false,
            },
            // buttons to activate
            buttons: {
                browse: true,
                start: true,
                stop: true
            },
            // Flash settings
            flash_swf_url : '/js/plupload/Moxie.swf',
            // Silverlight settings
            silverlight_xap_url : '/js/plupload/Moxie.xap',
            // PreInit events, bound before any internal events
            preinit : {
                Init: function(up, info) {
                    log('[Init]', 'Info:', info, 'Features:', up.features);
                },
                UploadFile: function(up, file) {
                    log('[UploadFile]', file);
                    // You can override settings before the file is uploaded
                    // up.setOption('url', 'upload.php?id=' + file.id);
                    // up.setOption('multipart_params', {param1 : 'value1', param2 : 'value2'});
                    up.setOption('multipart_params', {csrf_token : csrf});
                }
            },
            // Post init events, bound after the internal events
            init : {
                PostInit: function(up) {
                    // Called after initialization is finished and internal event handlers bound
                    log('[PostInit]');
                    files_uploaded_bib = 0;
                },
                Browse: function(up) {
                    // Called when file picker is clicked
                    log('[Browse]');
                },
                Refresh: function(up) {
                    // Called when the position or dimensions of the picker change
                    log('[Refresh]');
                },
                StateChanged: function(up) {
                    // Called when the state of the queue is changed
                    log('[StateChanged]', up.state == plupload.STARTED ? "STARTED" : "STOPPED");
                },
                QueueChanged: function(up) {
                    // Called when queue is changed by adding or removing files
                    log('[QueueChanged]');
                },
                OptionChanged: function(up, name, value, oldValue) {
                    // Called when one of the configuration options is changed
                    log('[OptionChanged]', 'Option Name: ', name, 'Value: ', value, 'Old Value: ', oldValue);
                },
                BeforeUpload: function(up, file) {
                    // Called right before the upload for a given file starts, can be used to cancel it if required
                    log('[BeforeUpload]', 'File: ', file);

                    var iframe_c = $("iframe.ui-layout-center");
                    var fid = file.id;
                    console.log('fid='+fid);
                    var filelist_line = $("#"+fid);
                    var c1 = filelist_line.children()[1];

                    // sending additional parameters
                    this.settings.multipart_params = {
                        "file_name" : file.name,
                        "data_extra" : $('#select_extra_' + fid).val()
                    };
                },
                UploadProgress: function(up, file) {
                    // Called while file is being uploaded
                    log('[UploadProgress]', 'File:', file, "Total:", up.total);
                },
                FileFiltered: function(up, file) {
                    // Called when file successfully files all the filters
                    log('[FileFiltered]', 'File:', file);
                },
                FilesAdded: function(up, files) {
                    // Called when files are added to queue
                    log('[FilesAdded]');
                    plupload.each(files, function(file) {
                        log('  File:', file);
                        //file.x = '777';
                        var iframe_c = $("iframe.ui-layout-center");
                        var fid = file.id;
                        console.log('fid='+fid);
                        var filelist_line = $("#"+fid);
                        console.log('filelist_line', filelist_line);

                        filelist_line.attr('class', 'progressContainer green');
                        var c1 = filelist_line.children()[1];
                        filename = file.name;
                        file_ext = filename.split('.').pop().toLowerCase();
                        var sel = '';
                        if (file_ext == 'bib') {
                            var sel = " <select name='tofiletype' class='select_unpack' id='select_extra_" + fid + "'>" +
                                "<option value='tofile'>" + js_upload_no_unpack + "</option>" +
                                "<option value='totype' selected>" + js_upload_unpack + "</option>" +
                            "</select>";
                        }
                        else {
                            /*
                            var sel = "<select name='tofiletype' id='select_extra_" + fid + "'>" +
                                "<option value='tofile'>To File (no unzip)</option>" +
                                "<option value='totype' selected>To typed nodes (unzip)</option>" +
                            "</select>";
                            */
                        }

                        c1.innerHTML = c1.innerHTML + sel;
                        c1ppp = c1.parentNode.parentNode.parentNode;
                        c1ppp.style.position = 'relative';
                        c1ppp.style.top = '0px';
                        c1ppp.style.overflow = 'auto';
                    });
                },
                FilesRemoved: function(up, files) {
                    // Called when files are removed from queue
                    log('[FilesRemoved]');
                    plupload.each(files, function(file) {
                        log('  File:', file);
                    });
                },
                FileUploaded: function(up, file, info) {
                    // Called when file has finished uploading
                    log('[FileUploaded] File:', file, "Info:", info);
                    var iframe_c = $("iframe.ui-layout-center");
                    var fid = file.id;
                    console.log('fid='+fid);
                    var filelist_line = $("#"+fid);
                    console.log('filelist_line', filelist_line);
                    if (JSON.parse(info.response).ret.indexOf('schema error') >= 0)
                      filelist_line.attr('class', 'progressContainer red');
                    else
                      filelist_line.attr('class', 'progressContainer blue');
                    var c1 = filelist_line.children()[1];
                    c1.innerHTML = c1.innerHTML + JSON.parse(info.response).ret;
                    c1ppp = c1.parentNode.parentNode.parentNode;
                    c1ppp.style.position = 'relative';
                    c1ppp.style.top = '0px';
                    c1ppp.style.overflow = 'auto';
                    $('#select_extra_' + fid).hide();

                    htree = parent.gethometree();
                    JSON.parse(info.response).new_tree_labels.forEach(
                        function(nentry) {
                        console.log('tree_node: '+nentry.id+', new label: '+nentry.label);
                        changed_node = htree.getNodeByKey(nentry.id);
                        changed_node.data.title = nentry.label;
                        changed_node.render();
                        }
                    );

                    uc = $('#uploaderbib_container');
                    x = uc.find('.ui-resizable-handle');
                    x.remove();

                    files_uploaded_bib = files_uploaded_bib + 1;
                },
                ChunkUploaded: function(up, file, info) {
                    // Called when file chunk has finished uploading
                    log('[ChunkUploaded] File:', file, "Info:", info);
                },
                UploadComplete: function(up, files) {
                    // Called when all files are either uploaded or failed
                    log('[UploadComplete]');
                    if (files_uploaded_bib > 0) {
                        $('#id_button_createobjectsplupload_bib').prop('disabled', false);
                    }
                },
                Destroy: function(up) {
                    // Called when uploaderfile is destroyed
                    log('[Destroy] ');
                },
                Error: function(up, args) {
                    // Called when error occurs
                    log('[Error] ', args);
                    alert(args.message + ': ' + args.file.name);
                }
            }
        });
    });
    return u;
}

function log() {
    var str = "";
    plupload.each(arguments, function(arg) {
        var row = "";

        if (typeof(arg) != "string") {
            plupload.each(arg, function(value, key) {
                // Convert items in File objects to human readable form
                if (arg instanceof plupload.File) {
                    // Convert status to human readable
                    switch (value) {
                        case plupload.QUEUED:
                            value = 'QUEUED';
                            break;

                        case plupload.UPLOADING:
                            value = 'UPLOADING';
                            break;

                        case plupload.FAILED:
                            value = 'FAILED';
                            break;

                        case plupload.DONE:
                            value = 'DONE';
                            break;
                    }
                }
                if (typeof(value) != "function") {
                    row += (row ? ', ' : '') + key + '=' + value;
                }
            });
            str += row + " ";
        } else {
            str += arg + " ";
        }
    });
    console.log(str);
};

// Handle the case when form was submitted before uploading has finished
$('#form').submit(function(e) {
    // Files in queue upload them first
    if ($('#uploaderfile').plupload('getFiles').length > 0) {
        // When all files are uploaded submit form
        $('#uploaderfile').on('complete', function() {
            $('#form')[0].submit();
        });
        $('#uploaderfile').plupload('start');
    } else if ($('#uploaderbib').plupload('getFiles').length > 0) {
        $('#uploaderbib').on('complete', function() {
            $('#form')[0].submit();
        });
        $('#uploaderbib').plupload('start');
    } else {
        alert("You must have at least one file in the queue.");
    }
    return false; // Keep the form from submitting
});

jQuery(document).ready(function($) {
    "use strict";
    showDebugMessages: true;
    sublayout = $('#sub_content').layout({
        applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content",},
        north:{paneSelector: "#navigation_content", size:north_size,resizable:false,},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0,},
        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed,
    });
});
