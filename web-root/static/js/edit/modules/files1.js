/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function removeItem(id, parent){
    $.get('/edit/edit_content?id='+parent+'&tab=files&style=popup&data=translate&msgstr=edit_files_removequestion&jsoncallback=?', function(data) {
        if (confirm(data)){
            $.get('/edit/edit_content?id='+parent+'&tab=files&style=popup&data=removeitem&remove='+id+'&jsoncallback=?', function(data) {
              $('#childnodes').html(data);
              return false;
            });
        }
    });
    return false;
}

function saveOrder(id){
    $.get('/edit/edit_content?id='+id+'&tab=files&style=popup&data=reorder&order='+$(".sortlist").html()+'&jsoncallback=?', function(data){});
    $("#orderdiv").css("display", "none");
    return false;
}

function sel(part){
    $('div[id^="file_"]').css('display', 'none');
    $('#'+part).css('display', 'block');
    return false;
}

function onNewVersionChecked (self) {
    if (self.checked) {
        $('#version_comment').show();
        $('#version_comment textarea').attr('required', '');
    } else {
        $('#version_comment').hide();
        $('#version_comment textarea').removeAttr('required');
    }
}

function setInput(item){
    if(item=="dir"){
        $('#inputname').css('display', 'block');
    }else{
        $('#inputname').css('display', 'none');
    }
}

$(document).ready(function () { // set correct height of scrollable content
   var sublayout = $('#sub_content').layout({applyDemoStyles: true,
        center:{paneSelector: "#sub_content_content", onresize: $.layout.callbacks.resizePaneAccordions},
        north:{paneSelector: "#navigation_content", size:10,resizable:false, closable:false},
        south:{paneSelector: "#sub_footer_module",size:20,closable:false, resizable:false, spacing_open: 0, spacing_closed: 0}
        });
    $("#accordion").accordion({heightStyle: "fill"});
});

$("#sortable" ).sortable({
    connectWith: ".connectedSortable",
    stop: function(event, ui) {
        $('.connectedSortable').each(function() {
            result = "";
            $(this).find("img").each(function(){
                if ($(this).attr("id")){
                    result += $(this).attr("id") + ",";
                }
            });
            if(result!=""){
                $("#orderdiv").css("display", "block");
                $(".sortlist").html(result);
            }
        });
    }
});
