/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function ckeditor_config(name) {
    var ckeditor = CKEDITOR.replace(name);
    ckeditor.config.toolbar = 'Meta';
    ckeditor.config.toolbar_Meta = [
        ['Source','Preview'],
        ['Cut','Copy','Paste','PasteText','PasteFromWord','-', 'SpellChecker', 'Scayt'],
        ['Undo','Redo','RemoveFormat'],
        '/',
        ['Bold','Italic','Underline','Strike','-','Subscript','Superscript'],
        ['JustifyLeft','JustifyCenter','JustifyRight','JustifyBlock'],
        ['NumberedList','BulletedList','-','Outdent','Indent','Blockquote'],
        [ 'Link', 'Unlink', 'Anchor' ],
        '/',
        ['Styles','Format','Font','FontSize','TextColor','BGColor','ShowBlocks']
    ];
    ckeditor.on('required', function(evt) {
        alert('Please fill out the htmlmemo field.');
        evt.cancel();
    });
}
