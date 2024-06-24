/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function ckeditor_config(name, entermode) {
    var ckeditor = CKEDITOR.replace(name);
    ckeditor.config.autoUpdateElement = false;
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
    ckeditor.config.enterMode = entermode==="br" ? CKEDITOR.ENTER_BR
        : entermode==="div" ? CKEDITOR.ENTER_DIV
        : CKEDITOR.ENTER_P;
    ckeditor.on('required', function(evt) {
        alert('Please fill out the htmlmemo field.');
        evt.cancel();
    });
    // Input listener only for "wysiwyg" mode
    ckeditor.on('change', function(event) {
        ckeditor.updateElement();
    });
    // On source wysiwyg switch
    ckeditor.on('mode', function(event) {
        if (this.editable().$.tagName === "TEXTAREA") {
            // Input listener only for "source" mode
            this.editable().$.addEventListener("input", function (event) {
                ckeditor.updateElement();
            });
        }
    });
    // After loading, check for a disabled parent element (e. g. admin area)
    ckeditor.once("instanceReady", function(evt) {
        let checkDisabled = document.createElement("input");
        checkDisabled.type = "hidden";
        checkDisabled.id = `a${Math.random().toString(36).substring(2)}`;
        ckeditor.container.$.before(checkDisabled);

        // Use the original element
        if (document.querySelector(`input#${checkDisabled.id}:disabled`) !== null) {
            ckeditor.destroy();
        }
        checkDisabled.parentNode.removeChild(checkDisabled);
    });
}
