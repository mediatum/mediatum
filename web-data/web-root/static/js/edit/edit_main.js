/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

$.getScript(
    "/static/fancytree/3rd-party/extensions/contextmenu/js/jquery.fancytree.contextMenu.js",
    function( data, sStatus, jqxhr ) { });

// some globals
var idselection = "";
var action = "";
var new_path_endpoint = "";

var flag_cut_mode = false;
var node_to_paste = null;  // node to be moves via context menu
var node_to_paste_classname = '';
var node_to_paste_li = null;

var last_activated_node = null;
var last_activated_tree_id_sel = null;

var tree = gethometree(); // check this

var FANCYTREE_KEYBOARD = true;
var FANCYTREE_DEFAULT_ICON = '/static/img/webtree/directory.svg';


function build_context_menu_items(node) {
    // no contextMenu for disabled nodes or descendants of cut node
    if ( node.li && node.li.classList.contains('fancytree-node-disabled') || (flag_cut_mode && node.isDescendantOf(node_to_paste)) ) {
        return false;
    }

    var create_container_items = {};

    containertype2iconpath.forEach(
        function(t){
            create_container_items['create_container_'+t[0]] = {name: t[1], icon:t[0]};
        }
    );

    var ctx_items = {
        "fornode": {name: node.title+"                                                                        ", disabled: true},
        "edit": {name: edit_t, icon: "edit"},
        "sep1": "---------",
        "submenu_create_container": {
                                      "name": addcontainer_t,
                                      "icon": "add",
                                      "items": create_container_items
                                    },
        "sep2": "---------",
        "cut_container": {name: cut_t, icon: "cut", disabled: flag_cut_mode},
        "paste_container_here": {name: paste_t, icon: "paste", disabled: !flag_cut_mode},
        "delete": {name: delete_t, icon: "delete", accesskey: "l", disabled: flag_cut_mode},
    };

    var special_dir_type = node.data.special_dir_type;

    if (typeof special_dir_type !== "undefined") {
      delete ctx_items["edit"];
      delete ctx_items["cut_container"];
      delete ctx_items["delete"];
    }

    if (special_dir_type === "trash") {
      ctx_items["clear_trash"] = {name: emptybin_t,
                                  icon: '/static/img/' + node.data.icon}
    }

    ctx_items["sep4"] = "---------";

    return ctx_items;
};


function hideContextMenuForNode(node) {
    try {
        $('#'+node.li.id).contextMenu('hide');
    }  catch  {}
}


function _paste_container_here(container, targetId)  {
    let src = container.parent.key;
    let obj = container.key;
    if (!($.isNumeric(src)))  src = container.parent.title;
    if (src === targetId)  {  // nothing to be done: user tries to paste node to parent
        flag_cut_mode = false;
        node_to_paste_li.removeClass('fancytree-node-disabled');
        return false;
    }
    if (!($.isNumeric(src) && $.isNumeric(obj) && $.isNumeric(targetId)))  {
        throw "moving node failed: node id is not an integer";
    }
    edit_action_sync('move', src, obj, targetId);
    flag_cut_mode = false;
    new_path_endpoint = obj;
    if (currentpath)  $('.ui-layout-center').attr('src',`/edit/edit_content?srcnodeid=${obj}&id=${obj}&tab=content`);
    return true;
}


function _tree_node_show_state(node, state)  {
    if (state==="loaded")  {
      node.setExpanded(true);
    }  else  if (state=="ok")  {
      node.setActive(true);
    }
}


function contextmenue_on_demand(selector, curtree, curtree_node_prefix, curkey) {
    // arguments: '#(h|c)tree-node-'+data.node.key, get(hometree|coltree)(), '(h|c)tree-node-', data.node
    $(function(){
        $.contextMenu({

            selector: selector,  // '#(h|c)tree-node-'+data.node.key

            autoHide: true,
            delay:200,
            zIndex:9999,

            build: function($trigger, e) {
                var node = curtree.getNodeByKey(curkey);

                // show contextMenu only for the active node
                if (!node.isActive()) {curtree.widget.options.keyboard = FANCYTREE_KEYBOARD; return false;};

                curtree.widget.options.keyboard = false;

                return {

                    items: build_context_menu_items(node),

                    events: {
                        hide: function(opt) {current_tree.widget.options.keyboard = FANCYTREE_KEYBOARD;},
                        show: function(opt) {
                            // show event is executed every time the menu is shown!
                            // find all clickable commands and set their title-attribute
                            // to their textContent value making the tooltip fulltext
                            // may be used to add help info as tooltext

                            var an = node;
                            opt.$menu.find('.context-menu-item > span').attr('title', function() {
                                return $(this).text();
                            });
                        } // show
                    },  // events


                    callback: function(action, opts) {
                        var res = false;  // return_value

                        var s = "create_container_";
                        if (action.substring(0, s.length) === s) {
                            var container_type = action.substring(s.length, action.length);
                            action = action.substring(0, s.length - 1); // create_container
                        }
                        hideContextMenuForNode(node); // hide the contextMenu
                        switch( action ) {
                            case "edit":
                                $('.ui-layout-center').attr('src', '/edit/edit_content?srcnodeid='+node.key+'&id='+node.key+'&tab=metadata');
                                res = false;
                                break;
                            case "create_container":
                                node.load(true);
                                node.setExpanded();
                                _add_new_container(container_type, node);

                                node.tree.loadKeyPath(currentpath, _tree_node_show_state);

                                if (currentpath) {
                                    $('.ui-layout-center').attr('src',
                                    '/edit/edit_content?srcnodeid='+new_path_endpoint+'&id='+new_path_endpoint+'&tab=metadata');
                                }

                                res = false;
                                break;
                            case "cut_container":
                                node_to_paste = node;
                                node_to_paste_li = $(node.li);
                                node_to_paste_classname = node_to_paste.li.className;

                                node_to_paste_li.addClass('fancytree-node-disabled');
                                flag_cut_mode = true;

                                // give tree keyboard focus so that cut mode may be canceled by "ESC" key
                                current_tree.widget.options.keyboard = FANCYTREE_KEYBOARD;
                                $(last_activated_tree_id_sel + ' .fancytree-container').focus();

                                res = false;
                                break;
                            case "paste_container_here":
                                if (_paste_container_here(node_to_paste, node.key))  {
                                    gethometree().reload();
                                    getcoltree().reload();
                                }
                                res = false;
                                break;
                            case "delete":
                                currentid = node.key;
                                questionOperation('delete'); // removes active node
                                res = false;
                                break;
                            case "clear_trash":
                                currentid = node.key;
                                questionOperation("clear_trash"); // removes active node
                                node.setActive();
                                res = false;
                                break;
                            case "quit":
                                res = false;
                                break;
                            default:
                                console.debug("Todo: appply action '" + action + "' to node " + node + '-' + node.title + '-' + node.key);
                                res = false;
                            }
                        current_tree.widget.options.keyboard = FANCYTREE_KEYBOARD;
                        return res;
                    }  // callback

                };  // return
            }  // build
        });  // contextMenu
    });  // function
}  // contextmenue_on_demand


function contextmenu_collections(selector) {
    $(function(){
        $.contextMenu({

            selector: selector,
            autoHide:true,
            delay:200,
            zIndex:9999,

            build: function($trigger, e) {
                var ctx_items = {
                    "edit": {name: edit_t, icon: "edit"},
                    "sep1": "---------",
                    "create_container_collection": {name: add_col_t, icon: "collection"},
                    "sep2": "---------",
                    "paste_container_here": {name: paste_t, icon: "paste", disabled: !flag_cut_mode},
                };

                return {
                    callback: function(key, options) {
                        if (key == "edit") {
                            $('.ui-layout-center').attr('src',
                            '/edit/edit_content?srcnodeid='+collectionsid+'&id='+collectionsid+'&tab=metadata');
                        }

                        if (key == "create_container_collection") {
                            _add_new_container("collection");
                            getcoltree().reload();
                        }
                        if (key == "paste_container_here") {
                            if (_paste_container_here(node_to_paste, collectionsid))  getcoltree().reload();
                        }
                    },

                items: ctx_items
                };
            }
        });
    });
}


contextmenu_collections('#collections');


function getcoltree() {
    return $("#mediatum_collectionstree").fancytree("getTree");
}

function gethometree() {
    return $("#hometree").fancytree("getTree");
}

function removeByKey(dtree, ckey) {
    var cnode = dtree.getNodeByKey(ckey);
    var pnode = cnode.getParent();
    var pnode_was_expanded = pnode.isExpanded();
    if (pnode) {
        try {
            cnode.li.hidden  = true;
            cnode.remove();
            if (pnode.isExpanded() != pnode_was_expanded) {
                pnode.toggleExpand();
            }
        }  catch  {}
    }
}


// source: http://stackoverflow.com/questions/123999/how-to-tell-if-a-dom-element-is-visible-in-the-current-viewport/7557433#7557433
function isElementInViewport(el) {

    //special bonus for those using jQuery
    if (el instanceof jQuery) {
        el = el[0];
    }

    var rect = el.getBoundingClientRect();

    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}


function reloadPage(id, path, tree_selector){
    var active_accordion = 1;  // #collectionstree
    if (typeof tree_selector === 'undefined' || tree_selector == '#hometree') {
        tree_selector = '#hometree';
        active_accordion = 0;
    }
    action = "";
    idselection = id;
    $('.ui-layout-center').attr('src', '/edit/edit_content?srcnodeid='+id+'&id='+id);
    $('.mediatum_accordiontree').accordion("option", "active", active_accordion);
    $(tree_selector).fancytree("getTree").loadKeyPath(path, function (node, state) {
        _tree_node_show_state(node, state);
        if ((state==="ok") && (!isElementInViewport(node.span))) {
            node.span.scrollIntoView();
        }
    });
    try {
        var usedtree = $(tree_selector).fancytree("getTree");
        var an = usedtree.activeNode;
        if (!isElementInViewport(an.span)) { // not needed for fancytree
            an.span.scrollIntoView();
        }
        an.load(forceReload=true);  // fancytree
        an.toggleExpanded();
        an.toggleExpanded();
    }  catch  {}

    return false;
}


function _add_new_container(type, parent_node)  {
    new_path_endpoint = false;
    var ajax_response;
    var parent_id = (parent_node) ? parent_node.key : collectionsid;
    $.ajax({
        url: '/edit/edit_action?srcnodeid='+parent_id+'&action=addcontainer&type='+type,
        async: false,
        dataType: 'json',
        success: function (response) { ajax_response = response; },
    });
    new_path_endpoint = ajax_response.key;
    if (parent_node)  {
        currentpath = currentpath + '/' + new_path_endpoint;
        parent_node.tree.getNodeByKey(parent_id).addChildren([ajax_response], parent_node.children[0]);
        parent_node.tree.activateKey(new_path_endpoint);
        parent_node.tree.activeNode.data.isFolder = true;
    }  else  {
        currentpath = new_path_endpoint;
    }
}


function questionOperation(type){
    if (type=='clear_trash'){
        var q = $("#mediatum_clear_trash_question").text();

        if(confirm(q)){

            var htree = $('#hometree').fancytree('getTree');

            var key_to_clear = currentid;

            var node_to_clear = htree.getNodeByKey(key_to_clear);

            node_to_clear.removeChildren()

            edit_action_sync(type, currentid, currentid);

            $("#hometree").fancytree("getTree").loadKeyPath(currentpath, _tree_node_show_state);

            node_to_clear.setActive();
            var activenode = $("#hometree").fancytree("getTree").activeNode;

            activenode.toggleExpanded();
            activenode.toggleExpanded();

            try {
                node_to_clear.removeChildren();
                node_to_clear.toggleExpanded();
                node_to_clear.toggleExpanded();
                }
            catch  {
                activenode.toggleExpanded();
                activenode.toggleExpanded();
            }
            loadEditArea(key_to_clear);

            return false;
        }

    } else if (type=='delete'){   // never reached?
        var q = $("#mediatum_delete_folder_question").text();

        if(confirm(q)){

            var cur_tree = current_tree;
            var key_to_delete = currentid;
            var node_to_delete = cur_tree.getNodeByKey(key_to_delete);
            var parent_node = node_to_delete.getParent();

            removeByKey(cur_tree, key_to_delete);

            edit_action_sync(type, currentid, currentid);

            cur_tree.loadKeyPath(currentpath, _tree_node_show_state);

            parent_node.setActive(true);
            var activenode = cur_tree.activeNode;
            activenode.toggleExpanded();
            activenode.toggleExpanded();

            try {
                parent_node.removeChild(node_to_delete);
                parent_node.toggleExpanded();
                parent_node.toggleExpanded();
            }  catch  {
                activenode.toggleExpanded();
                activenode.toggleExpanded();
            }
            htree = gethometree();
            trashdir = htree.getNodeByKey(user_folders.trashdir);
            trashdir.addChildren(node_to_delete);
            trashdir.load(forceReload=true);
            return false;
        }
    }
}


function cancelOperation(){
    action = "";
    tree.$(".mediatum_buttonmessage").html('');
}


function loadEditArea(id){
    $('.ui-layout-center').attr('src', '/edit/edit_content?srcnodeid='+ id + '&id=' + id);
}


var currentselection="";

var htree = null;
var ctree = null;

function reload_htree_filtered(homenodefilter) {
    if (!homenodefilter) {
        var homenodefilter = $('#homenodefilter').val();
    }
    var ht = gethometree();

    ht.widget.tree.options.source.data.homenodefilter = homenodefilter;
    ht.reload().done(function(){
        var homedir_key = user_folders['homedir'];
        var homedir = ht.getNodeByKey(homedir_key);
        var match_result = homedir.data.match_result;
        $('#htree_matches').html(match_result);
    }); // .done()
}

  // ############################################################################

tree_selector = "#hometree";
tree_node_id_prefix = "tree-node-";
tree_root_key = "home";  // "home", "root"
used_tree_selectors = ["#hometree", "#mediatum_collectionstree"];

function get_tree_opts(tree_selector, tree_node_id_prefix, tree_root_key, tree_root_nid, used_tree_selectors) {
    // options template for tree (htree and ctree)
    tree_opts = {

        autoFocus: false, // Set focus to first child, when expanding or lazy-loading.
        autoCollapse: false, // Automatically collapse all siblings, when a node is expanded.
        activeVisible: true, // Make sure, active nodes are visible (expanded).
        clickFolderMode: 1, // 1:activate, 2:expand, 3:activate and expand
        checkbox: false, // Show checkboxes.
        fx: { height: "toggle", duration: 200 }, // Animations, e.g. null or { height: "toggle", duration: 200 }
        idPrefix: tree_node_id_prefix, // Used to generate node id's like <span id="fancytree-id-<key>">.
        generateIds: true,
        minExpandLevel: 1, // 1: root node is not collapsible, 2, .., 4
        selectMode: 2, // 1:single, 2:multi, 3:multi-hier
        keyboard: FANCYTREE_KEYBOARD, // Support keyboard navigation.
        tabbable: true, // Whole tree behaves as one single control
        titlesTabbable: false, // Node titles can receive keyboard focus
        debugLevel: 1, // 0:quiet, 1:normal, 2:debug
        enableAspx: false, //Accept passing ajax data in a property named `d` (default: true).

        imagePath: '/static/img/',

        extensions: ["filter"],  //["persist", "filter"],

        filter: {
          mode: "hide"
        },

        createNode: function(event, data){
            var iconpath = data.node.data.icon;
            if (iconpath == "") {data.node.data.icon = FANCYTREE_DEFAULT_ICON;}
        },

        source: {
          url: "/edit/treedata",
          type: "POST",
          data: {key: tree_root_key, mode: "edittree", homenodefilter: $('#homenodefilter').val(), csrf_token: csrf},
          dataType: "json"
        },

        loadChildren: function(event, data) {
            data.node.visit(function(subNode){
                if( subNode.isUndefined() && subNode.isExpanded() ) {
                    subNode.load();
                }
            });
        },

        // Called when a lazy node is expanded for the first time
        lazyLoad: function(event, data){
            var node = data.node;
            // Load child nodes via ajax


            // synchronous loading
            var ajax_response;
            var options = {
                  url: '/edit/treedata?mode=edittree&key='+node.key,
                  async: false,
                  dataType: 'json',
                  success: function (response) {
                      ajax_response = response;
                  },
                };
            try {
              $(node.li).addClass('fancytree-loading');
            }  catch  {}
            $.ajax(options);
            data.result = ajax_response;
            try {
              $(node.li).removeClass('fancytree-loading');
            }  catch  {}
        },

        keydown: function(event, data){
            // Eat keyboard events, when a menu is open
            if( $(".context-menu-item:visible").length > 0 ) {
                // give keyboard focus to context menu; disable keyboard fo tree
                $('.context-menu-list .context-menu-root').focus();
                current_tree.widget.options.keyboard = false;

                return;
            }
            else{
                current_tree.widget.options.keyboard = FANCYTREE_KEYBOARD;
            }

            var node = data.node;
            if(event.key=="Enter" && node.data.readonly==0 && action==""){
                idselection = node.key;
                loadEditArea(node.key);
            }
            if(event.key==" " && node.data.readonly==0 && action==""){
                contextmenue_on_demand('#'+tree_node_id_prefix+data.node.key, $(tree_selector).fancytree("getTree"), tree_node_id_prefix,
                data.node.key);  // tree-dependent
                $('#'+tree_node_id_prefix+node.key+' span').contextMenu(); // show contextmenu programatically
                $('.context-menu-list .context-menu-root').focus();
                current_tree.widget.options.keyboard = false;
            }
            if(event.key=="Del" && node.data.readonly==0 && action==""){
                current_tree = $(this).fancytree("getTree");
                currentid = current_tree.activeNode.key;
                questionOperation('delete'); // removes active node
            }
            if(event.key=="Esc" && event.altKey==false && event.ctrlKey==false && event.metaKey==false) {
                hideContextMenuForNode(node);
                flag_cut_mode = false;
                action = "";
                try {
                    node_to_paste.li.className = node_to_paste_classname;
                }  catch  {}
            }

            switch( event.which ) {

                case 67:
                    if( event.ctrlKey ) { // Ctrl-C
                        copyPaste("copy", node);
                        return false;
                    }
                    break;
                case 86:
                    if( event.ctrlKey ) { // Ctrl-V
                        copyPaste("paste", node);
                        return false;
                    }
                    break;
                case 88:
                    if( event.ctrlKey ) { // Ctrl-X
                        copyPaste("cut", node);
                        return false;
                    }
                    break;
            }
        },  // keydown:

        // event click is fired befor activate
        click: function(event, data){
            var click_target_type = data.targetType;
            node = data.node;
            current_tree = $(this).fancytree("getTree");
            current_tree.widget.options.keyboard = FANCYTREE_KEYBOARD;
            currentpath = node.getKeyPath();
            tree.currentfolder = node.key;

            if(event.type=="fancytreeclick" && node.data.readonly==0 && action==""){
                idselection = node.key;
                loadEditArea(node.key);
            }
            else if (click_target_type == 'title' || click_target_type == 'icon') {
                var url = '&action='+encodeURIComponent(action);

                if (action=="move" || action=="copy"){
                    url = '&action='+encodeURIComponent(action)+'&dest='+node.key;
                }

                var ajax_response;

                var options = {
                    url: '/edit/edit_action?srcnodeid='+idselection+'&style=popup'+url,
                    async: false,
                    dataType: 'json',
                    type: 'POST',
                    traditional: true, //"would POST param "id[]" with brackets in the name otherwise
                    data: { ids: currentselection, csrf_token: csrf},
                    success: function (data) {
                        if (data!=""){
                            ajax_response = data;
                            ctree = getcoltree();  // ???  // more general solution needed ?
                            htree = gethometree();
                            if ('changednodes' in data) {
                                var changednodes = data.changednodes;
                                for (key in changednodes) {
                                    var changed_node = ctree.getNodeByKey(key);
                                    if (changed_node) {
                                        changed_node.title = changednodes[key];
                                        changed_node.renderTitle();
                                    }
                                    changed_node = htree.getNodeByKey(key);
                                    if (changed_node) {
                                        changed_node.title = changednodes[key];
                                        changed_node.renderTitle();
                                    }
                                }
                            }  // if ('changednodes' in data)

                            action = "";
                            loadEditArea(node.key);

                        }  // if (data!="")

                        return false;
                    }  // function (data)

                };  // options:

                $.ajax(options);
            }  // else if
        },  // click:

        activate: function(event, data) {
            var node = data.node;

            if (node.data.readonly == 1) {return;}

            last_activated_tree_id_sel = tree_selector;
            current_tree = $(this).fancytree("getTree");
            current_tree.widget.options.keyboard = FANCYTREE_KEYBOARD;
            idselection = node.key;
            // Close menu on click
            currentpath = node.getKeyPath();
            idselection = node.key;
            tree.currentfolder = node.key;
            contextmenue_on_demand('#'+tree_node_id_prefix+data.node.key, $(tree_selector).fancytree("getTree"), tree_node_id_prefix,
            data.node.key);  // tree-dependent
            $(node.span).removeClass('disabled');
            if( $(".contextMenu:visible").length > 0 ){
                $(".contextMenu").hide();
            }

            last_activated_node = node;

            if(event.type=="fanytreeclickactivate" && node.data.readonly==0 && action==""){
                idselection = node.key;
                loadEditArea(currentid);
            };

            if (flag_cut_mode) {
                disable_tree_nodes(
                        used_tree_selectors.map(function (selector) {return $(selector).fancytree("getTree")}),
                        [node_to_paste.key],
                       );
            }
        },  // activate:

        init: function(isReloading, isError){
            if (currentpath!="/"){
                $(this).fancytree("getTree").loadKeyPath(currentcpath, function(node, status){
                    if(status=="loaded"){ ;
                    }else if(status=="ok"){
                        node.setActive({noEvents: true});  // prevent folder content from being reloaded
                    }
                });
            }
        },

        postProcess: function(event, data) {  // check this
            data.tree.rootNode.setTitle(tree_root_nid);
            if (currentpath!="/")  {
                $(tree_selector).fancytree("getTree").loadKeyPath(currentpath, _tree_node_show_state);
            }
        }  // postProcess:

    }; // tree_opts

    return tree_opts;
}

$(document).ready(function () {
    layout = $('#body1').layout({
        applyDemoStyles: true,
        center__maskContents: true,
        north: {closable:false, resizable:false, spacing_open: 0, spacing_closed: 0, size:30},
        south: {closable:false, resizable:false, spacing_open: 0, spacing_closed: 0, size:20},
        west: {size:300,onresize: $.layout.callbacks.resizePaneAccordions,
            childOptions: {
                spacing_open: 0,
                spacing_closed:0,
                north: {paneSelector: ".mediatum_subnavigation", size:30},
                center:{paneSelector: ".mediatum_treecontent", onresize: $.layout.callbacks.resizePaneAccordions},
                south:{paneSelector:  ".mediatum_treesouth", closable:false, resizable:false, spacing_open: 0, spacing_closed: 0, size:21}
            }

        },
        resizerTip: js_edit_layout_resizertip,
        togglerTip_open: js_edit_layout_togglertip_open,
        togglerTip_closed: js_edit_layout_togglertip_closed
    });

    $(".mediatum_accordiontree").accordion({
        heightStyle: "fill", active: 1
    });

    // create home tree
    htree = $("#hometree").fancytree(get_tree_opts("#hometree", "htree-node-", "home", "INVALID", ["#hometree",
    "#mediatum_collectionstree"]));

    // create collections tree
    ctree = $("#mediatum_collectionstree").fancytree(get_tree_opts("#mediatum_collectionstree", "ctree-node-", "root", collectionsid,
    ["#hometree", "#mediatum_collectionstree"]));

    // close context menu when mouse is leaving pane
    var triggertarget = layout.panes.center;
    triggertarget.on('mouseover', function() {hideContextMenuForNode(last_activated_node);})

});  // $(document).ready(...)
