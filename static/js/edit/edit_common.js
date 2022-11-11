/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

$(document).ready(function() {
    previewimagesoff();
    $("#overlay>#text").html($('#overlay_content').html());
});

function previewimagesoff() {
    $("#mediatum_table_nodeview").hide();
    $("#mediatum_table_nodelist").show();
    $("#mediatum_grid_check").hide();
    $("#mediatum_showpreviewon").show();
    $('#mediatum_showpreviewoff').hide();
};

function previewimageson() {
    $("#mediatum_table_nodeview").show();
    $("#mediatum_table_nodelist").hide();
    $("#mediatum_grid_check").show();
    $('#mediatum_showpreviewoff').show();
    $("#mediatum_showpreviewon").hide();
};

function visitPage(id){
    window.location = $("#unpub").attr("href");
}

function closeSubOverlay(){
    $('#overlay').hide();
    action = '';
}
