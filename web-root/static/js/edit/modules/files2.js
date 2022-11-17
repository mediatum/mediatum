/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function setFolder(){
    getFolderItems(this.id);
    getGrandchildren(this.id);
    return false;
}

function getFolderItems(id){
    $.get('/edit/edit_content?style=popup&tab=files&data=children&id='+id+'&excludeid='+node+'&jsoncallback=?', function(data) {
      $('#files').html(data);
    });
}

function getFolderItemsExclude(folderid, excludeid){
    $.get('/edit/edit_content?style=popup&tab=files&data=children&id='+folderid+'&excludeid='+excludeid+'&jsoncallback=?', function(data) {
      $('#files').html(data);
    });
}

function getGrandchildren(folderid){
    $.get('/edit/edit_content?style=popup&tab=files&data=grandchildren&id='+folderid+'&excludeid='+node+'&jsoncallback=?', function(data) {
      $('#grandchildren').html(data);
    });
}

function selectedItems(srcnodeid){
    var val = "";
    $(":checkbox:checked[name=items_add]").each(
        function() {
            val += $(this).val()+";";
        }
    );
    $.get('/edit/edit_content?style=popup&tab=files&data=additems&srcnodeid='+srcnodeid+'&id='+node+'&items='+val, function(data) {
      opener.$('#childnodes').html(data);
      self.close();
    });
}

function select_all_grand(obj){
    $(':checkbox').each(function() {
        if(this.id=='grands_add'){
            this.checked = obj.checked;
        }
    });
}

function select_all_child(obj){
    $(':checkbox').each(function() {
        if(this.id=='child_add'){
            this.checked = obj.checked;
        }
    });
}
