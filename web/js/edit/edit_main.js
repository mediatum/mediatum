/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

consoledb.group('--- loading contextmenu js ---');
var ctx_mode = 1;  // 1: on_demand, 2: bind, 3: ui-contextmenu  // now only 1 supported, 2 and 3 abandoned
var url_ctx_on_demand = "/js/fancytree/3rd-party/extensions/contextmenu/jsx/jquery.fancytree.contextMenu.js";
var url_ctx_bind = "/js/jquery.contextMenu-custom-abs.js";
var url_ctx_ui = "//wwwendt.de/tech/demo/jquery-contextmenu/jquery.ui-contextmenu.js";

if (ctx_mode == 1) {
    url_ctx = url_ctx_on_demand;
}
else if (ctx_mode == 2) {
    url_ctx = url_ctx_bind;
}
else {
    url_ctx = url_ctx_ui;
}
$.getScript( url_ctx, function( data, sStatus, jqxhr ) {
    consoledb.log(sStatus); // Success
    consoledb.log(jqxhr.status ); // 200
    consoledb.log("loaded");
});
consoledb.groupEnd('--- loading contextmenu js ---');

// for older browsers such as IE8
// source: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/indexOf#Polyfill
if (!Array.prototype.indexOf) {
    Array.prototype.indexOf = function (searchElement, fromIndex) {
        if ( this === undefined || this === null ) {
            throw new TypeError( '"this" is null or not defined' );
        }

        var length = this.length >>> 0; // Hack to convert object.length to a UInt32

        fromIndex = +fromIndex || 0;

        if (Math.abs(fromIndex) === Infinity) {
            fromIndex = 0;
        }

        if (fromIndex < 0) {
            fromIndex += length;
            if (fromIndex < 0) {
                fromIndex = 0;
            }
        }

        for (;fromIndex < length; fromIndex++) {
            if (this[fromIndex] === searchElement) {
                return fromIndex;
            }
        }

        return -1;
    };
}

// some globals
var idselection = "";
var action = "";
var new_path_endpoint = "";

var flag_cut_mode = false;
var node_to_paste = null;  // node to be moves via context menu
var node_to_paste_classname = '';
var node_to_paste_li = null;

var dummy_temp = null;
var temp_ctx_event = null;
var temp_ctx_trigger = null;

var temp_node = null;

var last_activated_collectiontree_node = null;
var last_activated_hometree_node = null;
var last_activated_node = null;
var last_activated_tree_id_sel = null;

var last_click_event = null;

var tree = gethometree(); // check this

var ctree_dragstart_pnode_key = null;
var ctree_dragstop_pnode_key = null;

var last_ajax_result = null;

var FANCYTREE_KEYBOARD = true;
var FANCYTREE_DEFAULT_ICON = 'img/webtree/directory.gif';

function build_context_menu_items(node, opts) {

    consoledb.groupCollapsed('build_context_menu_items for node ' +  node.key + ', ' + node.title);

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
                                  icon: '../img/' + node.data.icon}
    }

    ctx_items["sep4"] = "---------";

    consoledb.groupEnd('build_context_menu_items for node ' +  node.key + ', ' + node.title);
    return ctx_items;
};


function showContextMenuForNode(node) {
    try {
        $('#'+node.li.id).contextMenu();
    }
    catch (e) {
        //consoledb.error('trying to showContextMenuForNode:', node, e);
        ;
    }
    var ctx = _tmp_opt_menu;
    return ctx;
}


function hideContextMenuForNode(node) {
    try {
        $('#'+node.li.id).contextMenu('hide');
    }
    catch (e) {
        //consoledb.error('trying to hideContextMenuForNode:', node, e);
        ;
    }
}


function callContextMenuCommandForNode(node, action, opt) {
    // opt: optional, may be omitted
    // important: node has to be active
    var ctx = showContextMenuForNode(node);
    var ctx_data = ctx.data();
    var res = ctx_data.contextMenu.callback(action, opt);
    hideContextMenuForNode(node);
    return res;
}

var _tmp_opt_menu = null;

function contextmenue_on_demand(selector, curtree, curtree_node_prefix, curkey) {
    // arguments: '#(h|c)tree-node-'+data.node.key, get(hometree|coltree)(), '(h|c)tree-node-', data.node
    $(function(){
        $.contextMenu({

            selector: selector,  // '#(h|c)tree-node-'+data.node.key

            autoHide: true,
            delay:200,
            zIndex:9999,

            build: function($trigger, e) {
                consoledb.groupCollapsed('contextMenu build for selector "' + selector + '"');
                consoledb.log("ctx_$trigger:", $trigger);
                consoledb.log("ctx_event:", e);

                temp_ctx_event = e;
                temp_ctx_trigger = $trigger;

                var node = curtree.getNodeByKey(curkey);

                // show contextMenu only for the active node
                if (!node.isActive()) {curtree.widget.options.keyboard = FANCYTREE_KEYBOARD; return false;};

                //$('.context-menu-list .context-menu-root').focus();
                curtree.widget.options.keyboard = false;

                consoledb.log('ctx menu for node ', node.key, node.title, node);
                consoledb.groupEnd('contextMenu build for selector "' + selector + '"');

                return {

                    items: build_context_menu_items(node),

                    events: {
                        hide: function(opt) {current_tree.widget.options.keyboard = FANCYTREE_KEYBOARD;},
                        show: function(opt) {
                            // show event is executed every time the menu is shown!
                            // find all clickable commands and set their title-attribute
                            // to their textContent value making the tooltip fulltext
                            // may be used to add help info as tooltext

                            consoledb.groupCollapsed('contextMenu events show');
                            var an = node;
                            consoledb.log(an.key, an.title, opt);
                            consoledb.log('opt: ', opt);
                            consoledb.log(opt.$menu);
                            _tmp_opt_menu = opt.$menu;

                            opt.$menu.find('.context-menu-item > span').attr('title', function() {
                                return $(this).text();
                            });
                            consoledb.groupEnd('contextMenu events show');
                        } // show
                    },  // events


                    callback: function(action, opts) {

                        consoledb.groupCollapsed('--- ctx_callback ---');
                        consoledb.log('action cut: ', action);
                        consoledb.log(opts);
                        consoledb.log('node.key: ' + node.key + ', node.title: ' + node.title);

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
                                consoledb.group('edit.html: create_container');
                                node.load(true);
                                node.setExpanded();
                                addNewContainer(node, container_type);

                                consoledb.log("should expand: " + currentpath);
                                node.tree.loadKeyPath(currentpath, function(node, status){
                                    if(status=="loaded"){
                                        node.setExpanded(true);
                                    }else if(status=="ok"){
                                        node.setActive(true);
                                    }
                                });

                                consoledb.log(1);
                                if (currentpath) {
                                    consoledb.log(2);
                                    $('.ui-layout-center').attr('src',
                                    '/edit/edit_content?srcnodeid='+new_path_endpoint+'&id='+new_path_endpoint+'&tab=metadata');
                                }
                                consoledb.log(3);

                                consoledb.groupEnd('edit.html: create_container')
                                res = false;
                                break;
                            case "cut_container":
                                consoledb.log('cut node:' + node.key);
                                consoledb.log('cut node has focus: ', node.hasFocus());
                                node_to_paste = node;
                                node_to_paste_li = $(node.li);
                                node_to_paste_classname = node_to_paste.li.className;
                                consoledb.log('cut node parent.key: ', node_to_paste.parent.key);

                                node_to_paste_li.addClass('fancytree-node-disabled');
                                flag_cut_mode = true;

                                // give tree keyboard focus so that cut mode may be canceled by "ESC" key
                                current_tree.widget.options.keyboard = FANCYTREE_KEYBOARD;
                                $(last_activated_tree_id_sel + ' .fancytree-container').focus();

                                res = false;
                                break;
                            case "paste_container_here":
                                consoledb.log('cut node:' + node.key);
                                var src = node_to_paste.parent.key;
                                var obj = node_to_paste.key;
                                var dest = node.key;
                                if(!($.isNumeric(src)))
                                {
                                    src = node_to_paste.parent.title;
                                    consoledb.log("src: ", src);
                                };
                                if (src == dest) { // nothing to be done: user tries to paste node to parent
                                    flag_cut_mode = false;
                                    node_to_paste_li.removeClass('fancytree-node-disabled');
                                    res = false;
                                    break;
                                }
                                consoledb.log("moving node "+obj+" from parent "+src+" to destination "+dest);
                                if (!($.isNumeric(src) && $.isNumeric(obj) && $.isNumeric(dest))) {
                                    throw "moving node failed: node id is not an integer";
                                };
                                ret = edit_action_sync('move', src, obj, dest);
                                consoledb.log("edit_action_sync finished: ", ret);
                                flag_cut_mode = false;
                                new_path_endpoint = obj;
                                if (currentpath) {
                                    consoledb.log(2);
                                    $('.ui-layout-center').attr('src',
                                    '/edit/edit_content?srcnodeid='+new_path_endpoint+'&id='+new_path_endpoint+'&tab=content');
                                }
                                consoledb.log("finished paste to: ", dest);
                                reloadHomeTree();
                                reloadColTree();
                                res = false;
                                break;
                            case "delete":
                                consoledb.log('---> new delete <---');
                                currentid = node.key;
                                var parent_node = node.getParent();
                                consoledb.log('action: '+action+', node'+node+', node.key:'+node.key+', parent_node.key:'+parent_node.key);
                                questionOperation('delete'); // removes active node
                                res = false;
                                break;
                            case "clear_trash":
                                currentid = node.key;
                                var parent_node = node.getParent();
                                consoledb.log('action: '+action+', node'+node+', node.key:'+node.key+', parent_node.key:'+parent_node.key);
                                questionOperation("clear_trash"); // removes active node
                                node.setActive();
                                res = false;
                                break;
                            case "quit":
                                res = false;
                                break;
                            default:
                                alert("Todo: appply action '" + action + "' to node " + node + '-' + node.title + '-' + node.key);
                                var keys = [];
                                for(var k in node.data) keys.push(k);
                                alert("total " + keys.length + " keys: " + keys);
                                alert("node.title: " + node.title);
                                alert("node.key  : " + node.key);
                                res = false;
                            }
                        current_tree.widget.options.keyboard = FANCYTREE_KEYBOARD;
                        consoledb.groupEnd('--- ctx_callback ---');
                        return res;
                    }  // callback

                };  // return
            }  // build
        });  // contextMenu
    });  // function
}  // contextmenue_on_demand


function contextmenu_collections(selector) {
    consoledb.log("contextmenu_collections collectionsid=", collectionsid);
    $(function(){
        $.contextMenu({

            selector: selector,
            autoHide:true,
            delay:200,
            zIndex:9999,

            build: function($trigger, e) {
                consoledb.log("$trigger:"+$trigger);
                consoledb.log("e:"+e);

                var ctx_items = {
                    "edit": {name: edit_t, icon: "edit"},
                    "sep1": "---------",
                    "create_container_collection": {name: add_col_t, icon: "collection"},
                    "sep2": "---------",
                    "paste_container_here": {name: paste_t, icon: "paste", disabled: !flag_cut_mode},
                };

                return {
                    callback: function(key, options) {
                        consoledb.log("key: " + key);

                        if (key == "edit") {
                            var m = "clicked: " + key;
                            window.console && consoledb.log(m);
                            $('.ui-layout-center').attr('src',
                            '/edit/edit_content?srcnodeid='+collectionsid+'&id='+collectionsid+'&tab=metadata');
                        }

                        if (key == "create_container_collection") {
                            var p = "clicked: " + key;
                            window.console && consoledb.log(p);

                            addNewContainerToRoot("collection");
                            reloadColTree();
                        }
                        if (key == "paste_container_here") {
                            consoledb.log("paste_container_here: ", collectionsid);
                            var src = node_to_paste.parent.key;
                            var obj = node_to_paste.key;
                            var dest = collectionsid;
                            if(!($.isNumeric(src)))
                            {
                                src = node_to_paste.parent.title;
                                consoledb.log("src: ", src);
                            };
                            if (src == dest) { // nothing to be done: user tries to paste node to parent
                                flag_cut_mode = false;
                                node_to_paste_li.removeClass('fancytree-node-disabled');
                            }
                            else
                            {
                                consoledb.log("moving node "+obj+" from parent "+src+" to destination "+dest);
                                if (!($.isNumeric(src) && $.isNumeric(obj) && $.isNumeric(dest))) {
                                    throw "moving node failed: node id is not an integer";
                                };
                                ret = edit_action_sync('move', src, obj, dest);
                                consoledb.log("edit_action_sync finished: ", ret);
                                flag_cut_mode = false;
                                new_path_endpoint = obj;
                                if (currentpath) {
                                    $('.ui-layout-center').attr('src',
                                    '/edit/edit_content?srcnodeid='+new_path_endpoint+'&id='+new_path_endpoint+'&tab=content');
                                }
                                consoledb.log("finished paste to: ", dest);
                                reloadColTree();
                            }
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
        }
        catch(e) {
            consoledb.log('removeByKey for key='+ckey+' caught: '+e);
        }
    }
}

function reloadColTree(){
    $("#mediatum_collectionstree").fancytree("getTree").reload();
}

function reloadHomeTree(){
    $("#hometree").fancytree("getTree").reload();
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
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && /*or $(window).height() */
        rect.right <= (window.innerWidth || document.documentElement.clientWidth) /*or $(window).width() */
    );
}


function reloadPage(id, path, tree_selector){
    consoledb.log('web/edit/edit.html: function reloadPage(id, path): id: '+id+', path: '+path);
    var active_accordion = 1;  // #collectionstree
    if (typeof tree_selector === 'undefined' || tree_selector == '#hometree') {
        tree_selector = '#hometree';
        active_accordion = 0;
    }
    action = "";
    idselection = id;
    consoledb.log(path);
    $('.ui-layout-center').attr('src', '/edit/edit_content?srcnodeid='+id+'&id='+id);
    $('.mediatum_accordiontree').accordion("option", "active", active_accordion);
    $(tree_selector).fancytree("getTree").loadKeyPath(path, function(node, status){
        consoledb.log('arguments: ', arguments);
        if(status=="loaded"){
            node.setExpanded(true);
        }else if(status=="ok"){
            node.setActive(true);
            if (!isElementInViewport(node.span)) {
              node.span.scrollIntoView();
            }
        }else{
            var seg = arguments[2], isEndNode = arguments[3];
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
    }
    catch(e) {
        consoledb.log('tried to reloadChildren(), caught: '+e);
    }

    return false;
}


function addNewContainerToRoot(type){ /* add new container */
    new_path_endpoint = false;
    var ajax_response;
    consoledb.log('addNewContainerToRoot: collectionsid=', collectionsid);
    var parent_id = collectionsid;
    var options = {
        url: '/edit/edit_action?srcnodeid='+parent_id+'&action=addcontainer&type='+type,
        async: false,
        dataType: 'json',
        success: function (response) {
            ajax_response = response;
            new_path_endpoint = response.key;

            currentpath = response.key;

            consoledb.log('$.ajax returns: '+response);
            consoledb.log('currentpath: '+currentpath);
        },
    };

    $.ajax(options);
}

function addNewContainer(parent_node, type){ /* add new container */
    new_path_endpoint = false;
    var ajax_response;
    var parent_id = parent_node.key;
    consoledb.log('addNewContainer: parent_node.key '+parent_node.key);
    var options = {
          url: '/edit/edit_action?srcnodeid='+parent_id+'&action=addcontainer&type='+type,
          async: false,
          dataType: 'json',
          success: function (response) {
              ajax_response = response;
              new_path_endpoint = response.key;
              currentpath = currentpath + '/' + response.key;
              consoledb.log('$.ajax returns: '+response);
              consoledb.log('currentpath: '+currentpath);
          },
    };

    $.ajax(options);

    var childnode = ajax_response;
    parent_node.tree.getNodeByKey(parent_id).addChildren([childnode], parent_node.children[0]);
    parent_node.tree.activateKey(new_path_endpoint);
    parent_node.tree.activeNode.data.isFolder = true;
    consoledb.log('activeNode:', parent_node.tree.activeNode.key);
    consoledb.log('parent_node.tree.activeNode.data.isFolder:', parent_node.tree.activeNode.data.isFolder);
}


function questionOperation(type){

    consoledb.group('edit: edit.html: questionOperation('+type+')');

    if (type=='clear_trash'){
        var q = $("#mediatum_clear_trash_question").text();

        if(confirm(q)){

            var htree = $('#hometree').fancytree('getTree');

            var key_to_clear = currentid;

            var node_to_clear = htree.getNodeByKey(key_to_clear);
            var parent_node = node_to_clear.getParent();
            var parent_node_key = parent_node.key;

            // some operations may take time ... indicate activity with wait.gif
            // var node_to_clear_old_title = node_to_clear.data.title;
            //node_to_clear.setTitle(node_to_clear_old_title + '<img height="30" src="/img/wait.gif" />');

            node_to_clear.removeChildren()

            edit_action_sync(type, currentid, currentid);

            consoledb.log('currentid  :'+currentid);
            consoledb.log('currentpath:'+currentpath);

            $("#hometree").fancytree("getTree").loadKeyPath(currentpath, function(node, status){
                if(status=="loaded"){
                    node.setExpanded();
                }else if(status=="ok"){
                    node.setActive();
                }
            });

            node_to_clear.setActive();
            var activenode = $("#hometree").fancytree("getTree").activeNode;

            activenode.toggleExpanded();
            activenode.toggleExpanded();

            try {
                node_to_clear.removeChildren();
                node_to_clear.toggleExpanded();
                node_to_clear.toggleExpanded();
                }
            catch(e) {
                consoledb.log('caught exeption :' + e);
                activenode.toggleExpanded();
                activenode.toggleExpanded();
            }
            loadEditArea(key_to_clear);
            consoledb.groupEnd('edit: edit.html: questionOperation('+type+')');

            return false;
        }

    } else if (type=='delete'){   // never reached?
        var q = $("#mediatum_delete_folder_question").text();

        consoledb.log('currentid  :'+currentid);
        consoledb.log('currentpath:'+currentpath);

        if(confirm(q)){

            var cur_tree = current_tree;
            var key_to_delete = currentid;
            var node_to_delete = cur_tree.getNodeByKey(key_to_delete);
            var parent_node = node_to_delete.getParent();
            var parent_node_key = parent_node.key;

            removeByKey(cur_tree, key_to_delete);

            edit_action_sync(type, currentid, currentid);

            consoledb.log('currentid  :'+currentid);
            consoledb.log('currentpath:'+currentpath);

            cur_tree.loadKeyPath(currentpath, function(node, status){
                if(status=="loaded"){
                    node.setExpanded(true);
                }else if(status=="ok"){
                    node.setActive(true);
                }
            });

            parent_node.setActive(true);
            var activenode = cur_tree.activeNode;
            activenode.toggleExpanded();
            activenode.toggleExpanded();

            try {
                parent_node.removeChild(node_to_delete);
                parent_node.toggleExpanded();
                parent_node.toggleExpanded();
                }
            catch(e) {
                consoledb.log('caught exeption :' + e);
                activenode.toggleExpanded();
                activenode.toggleExpanded();
            }
            htree = gethometree();
            trashdir_key = user_folders.trashdir;
            trashdir = htree.getNodeByKey(trashdir_key);
            trashdir.addChildren(node_to_delete);
            trashdir.load(forceReload=true);
            consoledb.groupEnd('edit: edit.html: questionOperation('+type+')');
            return false;
        }
    }
}


function cancelOperation(){
    action = "";
    tree.$(".mediatum_buttonmessage").html('');
}

function addItem(id, path){  // currently unused
    action = "";
    idselection = "";
    consoledb.log(path);
    $('.ui-layout-center').attr('src', '/edit/edit_content?srcnodeid='+id+'&id='+id+"&upload=visible&r="+""+Math.random()*10000);
    $('.mediatum_accordiontree').accordion("option", "active", 0);
    $("#hometree").fancytree("getTree").loadKeyPath(path, function(node, status){
        if(status=="loaded"){
            node.setExpanded();
        }else if(status=="ok"){
            node.setActive();
        }else{
            var seg = arguments[2], isEndNode = arguments[3];
        }
    });
    try {
        $("#hometree").fancytree("getActiveNode").reloadChildren();
    }
    catch(e) {
        consoledb.log('tried to reloadChildren(), caught: '+e);
    }
    return false;
}

function loadEditArea(id){
    $('.ui-layout-center').attr('src', '/edit/edit_content?srcnodeid='+ id + '&id=' + id);
}

function set_cm_to_default() {
    flag_cut_mode = false;
    consoledb.log('set_cm_to_default: flag_cut_mode =', flag_cut_mode);
}

var rct = null;
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

function get_used_trees (selector_list) {
    res = selector_list.map(function (selector) {return $(selector).fancytree("getTree")});
    return res;
}

function get_tree_opts(tree_selector, tree_node_id_prefix, tree_root_key, tree_root_nid, used_tree_selectors) {
    // options template for tree (htree and ctree)
    tree_opts = {

        autoFocus: false, // Set focus to first child, when expanding or lazy-loading.
        autoCollapse: false, // Automatically collapse all siblings, when a node is expanded.
        //autoScroll: true,
        activeVisible: true, // Make sure, active nodes are visible (expanded).
        clickFolderMode: 1, // 1:activate, 2:expand, 3:activate and expand
        checkbox: false, // Show checkboxes.
        fx: { height: "toggle", duration: 200 }, // Animations, e.g. null or { height: "toggle", duration: 200 }
        idPrefix: tree_node_id_prefix, // Used to generate node id's like <span id="fancytree-id-<key>">.
        generateIds: true,
        minExpandLevel: 1, // 1: root node is not collapsible, 2, .., 4
        //nolink: false, // Use <span> instead of <a> tags for all nodes
        selectMode: 2, // 1:single, 2:multi, 3:multi-hier
        keyboard: FANCYTREE_KEYBOARD, // Support keyboard navigation.
        tabbable: true, // Whole tree behaves as one single control
        titlesTabbable: false, // Node titles can receive keyboard focus
        debugLevel: 1, // 0:quiet, 1:normal, 2:debug
        enableAspx: false, //Accept passing ajax data in a property named `d` (default: true).

        imagePath: '../img/',

        extensions: ["filter"],  //["persist", "filter"],

        filter: {
          mode: "hide"
        },

        createNode: function(event, data){
            consoledb.log('--- tree createNode ---');
            consoledb.log(event);
            consoledb.log(data);
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
            consoledb.log('--- lazyLoad ---');
            consoledb.log(event);
            consoledb.log(data);
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
            }
            catch (e) {
             ;
            }
            $.ajax(options);
            data.result = ajax_response;
            try {
              $(node.li).removeClass('fancytree-loading');
            }
            catch (e) {
             ;
            }
        },

        keydown: function(event, data){
            consoledb.log('--- keydown ---');
            consoledb.log('event:', event);
            consoledb.log('event.key:', "'"+event.key+"'",'event.altKey:', event.altKey,'event.ctrlKey:', event.ctrlKey,'event.metaKey:', event.metaKey);
            consoledb.log('data:', data);

            // Eat keyboard events, when a menu is open
            if( $(".context-menu-item:visible").length > 0 ) {
                consoledb.log('detected ctx-menu');

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
                // 2014-11-26
                contextmenue_on_demand('#'+tree_node_id_prefix+data.node.key, $(tree_selector).fancytree("getTree"), tree_node_id_prefix,
                data.node.key);  // tree-dependent
                $('#'+tree_node_id_prefix+node.key+' span').contextMenu(); // show contextmenu programatically
                $('.context-menu-list .context-menu-root').focus();
                current_tree.widget.options.keyboard = false;
            }
            if(event.key=="Del" && node.data.readonly==0 && action==""){
                consoledb.log('going to remove active node');
                current_tree = $(this).fancytree("getTree");
                currentid = current_tree.activeNode.key;
                questionOperation('delete'); // removes active node
            }
            if(event.key=="Esc" && event.altKey==false && event.ctrlKey==false && event.metaKey==false) {
                consoledb.log('Esc key pressed');
                hideContextMenuForNode(node);
                set_cm_to_default();
                action = "";
                try {
                    node_to_paste.li.className = node_to_paste_classname;
                }
                catch(e) {
                    ;
                }
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
            consoledb.log('#### click ####: ', click_target_type);
            consoledb.log(event);
            consoledb.log('event.type: ' + event.type);
            consoledb.log('action click: ', action);
            last_click_event = event;

            node = data.node;
            consoledb.log(data);
            consoledb.log('---> node.data.readonly: ' + node.data.readonly);
            current_tree = $(this).fancytree("getTree");
            current_tree.widget.options.keyboard = FANCYTREE_KEYBOARD;
            currentpath = node.getKeyPath();
            tree.currentfolder = node.key;

            if(event.type=="fancytreeclick" && node.data.readonly==0 && action==""){
                idselection = node.key;
                loadEditArea(node.key);
            }
            else if (click_target_type == 'title' || click_target_type == 'icon') {

                consoledb.groupCollapsed('tree onClick with action');
                consoledb.log('action: '+action);

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
                        consoledb.log('entering callback function ...');
                        if (data!=""){
                            var msg = '-- after action: '+action+' --: '+data;
                            consoledb.log(msg);
                            ajax_response = data;
                            ctree = getcoltree();  // ???  // more general solution needed ?
                            htree = gethometree();
                            if ('changednodes' in data) {
                                var changednodes = data.changednodes;
                                for (key in changednodes) {
                                    consoledb.log(key);
                                    consoledb.log(changednodes[key]);
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
                consoledb.groupEnd('tree onClick');
            }  // else if
        },  // click:

        activate: function(event, data) {
            consoledb.log('--- activate ---', data.node.title, data.node.key);
            consoledb.log(event);
            consoledb.log(data);
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
            // 2014-11-26
            contextmenue_on_demand('#'+tree_node_id_prefix+data.node.key, $(tree_selector).fancytree("getTree"), tree_node_id_prefix,
            data.node.key);  // tree-dependent
            $(node.span).removeClass('disabled');
            if( $(".contextMenu:visible").length > 0 ){
                $(".contextMenu").hide();
            }

            last_activated_node = last_activated_hometree_node = node;

            if(event.type=="fanytreeclickactivate" && node.data.readonly==0 && action==""){
                idselection = node.key;
                loadEditArea(currentid);
            };

            if (flag_cut_mode) {
                disable_tree_nodes(get_used_trees(used_tree_selectors), [node_to_paste.key]);
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
            consoledb.log('--- tree postProcess ---');
            consoledb.log('event:', event, 'data:', data);
            data.tree.rootNode.setTitle(tree_root_nid);
            if (currentpath!="/"){
                //var node = data.node;
                var thistree = $(tree_selector).fancytree("getTree");
                thistree.loadKeyPath(currentpath, function(node, status){
                    if(status=="loaded"){
                        node.setExpanded();
                    }else if(status=="ok"){
                        node.setActive();
                    }
                });
            }
        }  // postProcess:

    }; // tree_opts

    return tree_opts;
}

$(document).ready(function () {
    consoledb.log('document ready function #002');

    $('.context-menu-collections').on('click', function(e){
        consoledb.log('clicked context-menu-collections', this);
    })

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

function __load(path){
    consoledb.log('called edit.html: __load(path)');
    $("#mediatum_collectionstree").fancytree("getTree").loadKeyPath(path, function(node, status){
        consoledb.log('load');

        if(status=="loaded"){
            //node.toggleExpanded(); //expand();
            //node.toggleExpanded();
            node.setExpanded();
        }else if(status=="ok"){
            node.setActive();
        }else{
            var seg = arguments[2], isEndNode = arguments[3];
            consoledb.log(seg);
        }
    });
}

// reload collections tree
function rct() {
    consoledb.group('edit.html: rct()');
    consoledb.log('currentpath: '+ currentpath);
    ctree = getcoltree();
    consoledb.log('acquired ctree');
    htree = gethometree();
    consoledb.log('acquired htree');
    if (current_tree == ctree) {
        consoledb.log('true: current_tree == ctree');
        $("#mediatum_collectionstree").fancytree("getTree").reload();
    }
    if (current_tree == htree) {
        consoledb.log('true: current_tree == htree');
        $("#hometree").fancytree("getTree").reload();
        consoledb.log('htree reloaded');
        consoledb.log('loaded key path');
    }
    consoledb.groupEnd('edit.html: rct()');
};
