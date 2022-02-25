var i = 0;
var value = "";
var selected = false;
var checkselect = 0;
var spancount = 1;
var spanid = 0;

var userSelection = "";// """ + usersel + """;
var groupSelection = ""; //""" + groupsel + """;
var dateSelection = ""; // """ + datesel + """;
var ipSelection = ""; //""" + ipsel + """;


function init(userstr, groupstr, datestr, ipstr)
{
    userSelection = userstr;
    groupSelection = groupstr;
    dateSelection = datestr;
    ipSelection = ipstr;
    setMainRule();
}



function ReplaceTags(xStr)
{
    xStr = xStr.replace(/[\r\n\t]/gi,"");
    xStr = xStr.replace(/<\/?[^>]+>/gi,"");
    xStr = xStr.replace(/&lt;/gi,"<");
    xStr = xStr.replace(/&gt;/gi,">");
    value = xStr;
    return xStr;
}

function pick(obj)
{
    if (selected==false)
    {
        i++;
        if (i==1)
        {
            obj.style.border = "solid red 1px";
            obj.style.cursor ="pointer";
            obj.style.cursor ="hand";
            obj.style.margin="1px";
            spanid=obj.id;
        }
    }    
}

function unpick(obj)
{
    if (selected==false)
    {
        obj.style.border = "solid white 1px";
        i=0;
        obj.style.margin="1px";
        spanid = 0;
    }
}

function selectpart(obj)
{
    if (checkselect == 0)
        checkselect = obj.id;

    if (checkselect==obj.id)
    {
        if (selected==true)
            selected=false;
        else
            selected=true;
        document.getElementById("rule_part").innerHTML = ReplaceTags(document.getElementById(obj.id).innerHTML);
    }
    if (obj.id==1)
        checkselect=0;
}

function setValue(obj)
{
    if (obj.name=="ruleop")
    {

        if (document.getElementById("rule_part").innerHTML=="date "){
            document.getElementById("rule_part").innerHTML += document.getElementById(obj.name).value;
        }
    }
    else if(obj.name=="rulearg" )
    {
        if (document.getElementById("rulearg").value=="user ")
        {
            document.getElementById("argspan").innerHTML = userSelection;
        }
        else if (document.getElementById("rulearg").value=="group ")
        {
            document.getElementById("argspan").innerHTML = groupSelection;
        }
        else if(document.getElementById("rulearg").value=="date ")
        {
            document.getElementById("argspan").innerHTML = dateSelection;
        }
        else if(document.getElementById("rulearg").value=="ip ")
        {
            document.getElementById("argspan").innerHTML = ipSelection;
        }
        document.getElementById("rule_part").innerHTML = document.getElementById(obj.name).value;
    }
    else if(obj.name=="users" || obj.name=="groups")
    {
        document.getElementById("rule_part").innerHTML += document.getElementById(obj.name).value;
        document.getElementById("argspan").innerHTML="&nbsp;";
    }
    else if(obj.name=="dateselect")
    {
        if (document.getElementById("datevalue").value.length==10)
        {
            document.getElementById("rule_part").innerHTML += document.getElementById("datevalue").value;
            document.getElementById("argspan").innerHTML = "&nbsp;";
        }
    }
    else if(obj.name=="ipselect")
    {
        if (document.getElementById("ipvalue").value!="")
        {
            document.getElementById("rule_part").innerHTML += document.getElementById("ipvalue").value;
            document.getElementById("argspan").innerHTML = "&nbsp;";
        }

    }
    else if(obj.name=="ruletype")
    {
        rulestr = document.getElementById(obj.name).value;
        if (rulestr.indexOf("[op1]")>0 && document.getElementById("value1").value!="")
        {
            position = rulestr.indexOf("[op1]");
            rulestr = rulestr.substring(0,position) + document.getElementById("value1").value + rulestr.substring(position+5);
        }

        if (rulestr.indexOf("[op2]")>0 && document.getElementById("value2").value!="")
        {
            position = rulestr.indexOf("[op2]");
            rulestr = rulestr.substring(0,position) + document.getElementById("value2").value + rulestr.substring(position+5);
        }

        document.getElementById("rule_part").innerHTML = rulestr;
    }
}

function setPart()
{
    var value = document.getElementById("rule_part").innerHTML;
    if (value.substring(0,1) != "(")
    {
        value= "( " + value + " )";
    }
    value = value.replace("&lt;","<");
    value = value.replace("&gt;",">");
    option = new Option(value, value, false, false);
    document.getElementById("parts").options[document.getElementById("parts").length] = option;
    document.getElementById("rule_part").innerHTML ="";
    document.getElementById("argspan").innerHTML ="&nbsp;";
}

function changePart()
{
    if (selected==true)
    {
        var value= document.getElementById("rule_part").innerHTML;
        if (value !="")
        {

            if (value.substring(0,1) != "(")
            {
                value= "( " + value + " )";
            }
            document.getElementById(spanid).innerHTML = replaceBracket(value);
        }
    }
}

function clearParts()
{
    document.getElementById("parts").length=null;
}

function setOperator()
{

    if (document.getElementById("op").checked)
    {
        document.getElementById("value1").value= document.getElementById("parts").value;
    }
    else
    {
        document.getElementById("value2").value= document.getElementById("parts").value;
    }
}

function replaceBracket(value)
{
    value = value.replace(/[)]/gi,")</span>");
    value = value.replace(/[(]/gi,"<span class='rule' id='!' ONMOUSEOVER='pick(this)' ONMOUSEOUT='unpick(this)' ONCLICK='selectpart(this)'>(");
    position = 0;
    while( value.indexOf("!")>0)
    {
        position = value.indexOf("!");
        value = value.substring(0,position) + spancount + value.substring(position+1);
        spancount++;
    }
    return value;
}

function setMainRule()
{
    var value = "( true )";
    if (opener.getEditRule()!="")
    {
        value=opener.getEditRule();
    }
    if(value.indexOf("(")!=-1)
    {
        document.getElementById("MainRule").innerHTML = replaceBracket(value);
    }
    else
    {
        document.getElementById("MainRule").innerHTML = replaceBracket("(" + value + ")");
    }
}

function setReturn()
{
    opener.getEditorValue( ReplaceTags(document.getElementById("MainRule").innerHTML));
    self.close();
}

function getSelectedValue()
{
    document.getElementById("rule_part").innerHTML = document.getElementById("parts").value;
}

function showACLGroup(){
    obj = document.getElementById("acl_div");
    obj.style.display="block";
    obj = document.getElementById("user_div");
    obj.style.display="none";
    
    obj = document.getElementById("type");
    obj.value = "acl";
}

function showACLUser(){
    obj = document.getElementById("acl_div");
    obj.style.display="none";
    obj = document.getElementById("user_div");
    obj.style.display="block";
    
    obj = document.getElementById("type");
    obj.value = "user";
}


function getEditPage(destname, nodeid, tab, action){
    var url = '/edit/edit_content?srcnodeid='+nodeid+'&id='+nodeid;
    if (tab!=""){
        url+='&tab='+tab;
    }
    if (action!=""){
        url+='&action='+action;
    }

    $.get(url+'&style=popup', function(data){
        $('#'+destname).html(data);
    });
}


function edit_action(action, src, ids, add){
    var url = '&action='+escape(action);
    if(add==1){ // folder
        url = '&newfolder='+escape(action);
    }else if (add==2){ //collection
        url = '&newcollection='+escape(action);
    }
    if (action=="move" || action=="copy"){
        url = '&action='+escape(action)+'&dest='+add;
    }
    
    $.get('/edit/edit_action?srcnodeid='+src+'&ids='+ids+'&style=popup'+url, function(data){
       
        if (data!=""){
            return data;
        }
    });
}

DEBUG_MODE = true;  // using console for debugging msg

if (DEBUG_MODE && window.console) {
  consoledb = window.console;
}
else {
  do_nothing = function() {};
  consoledb = {};
  consoledb.log = consoledb.info = consoledb.error = consoledb.warn = consoledb.debug = do_nothing;
  consoledb.group = consoledb.groupCollapsed = consoledb.groupEnd = do_nothing;
  consoledb.dir = consoledb.dirxml = do_nothing;
}


function disable_tree_nodes(used_trees, pids) {
            consoledb.groupCollapsed('--- disable_tree_nodes ---');
            for (var i in used_trees) {
              used_tree = used_trees[i];
              for (var index in pids) {
                  var pid = pids[index];
                  consoledb.log('--------> ', index, pid);
                  var testnode = used_tree.getNodeByKey(pid);
                  if (!testnode) {
                      continue;
                  }
                  $(testnode.li).addClass('fancytree-node-disabled');
              }  
            }
            consoledb.groupEnd('--- disable_tree_nodes ---');
}


function update_tree_nodes_labels(used_trees, changednodes) {
            consoledb.groupCollapsed('--- update_tree_nodes_labels ---');
            for (var i in used_trees) {
              used_tree = used_trees[i];
              for (var key in changednodes) {
                  consoledb.log(key);
                  var new_label = changednodes[key];
                  consoledb.log(new_label);
                  consoledb.log('new label for key '+key+': '+new_label);
                  var changed_node = used_tree.getNodeByKey(key);
                  if (!changed_node) {
                      continue;
                  }
                  changed_node.title = new_label;
                  changed_node.renderTitle();
              }  
            }
            consoledb.groupEnd('--- update_tree_nodes_labels ---');
}


function reload_tree_nodes_children(used_trees, pids) {
            consoledb.groupCollapsed('--- reload_tree_nodes_children ---');
            consoledb.log('--> pids: ' + pids);

            for (var i in used_trees) {
              used_tree = used_trees[i];
              consoledb.log('----> tree index', i);
              for (var index in pids) {
                  consoledb.log('------> pid index', index);
                  var key = pids[index];
                  consoledb.log('------> pid', key);

                  var parentnode = used_tree.getNodeByKey(key);

                  if (!parentnode) {
                      consoledb.log('------> continue');
                      continue;
                  }
                  consoledb.log('------> parentnode:', parentnode.title, parentnode);
                  var pn_expanded = parentnode.isExpanded();
                  consoledb.log('------> parentnode.isExpanded():', pn_expanded);
                  parentnode.load(forceReload=true).done(function() {
                    parentnode.setExpanded(pn_expanded);
                    });
              }  
            }
            consoledb.groupEnd('--- reload_tree_nodes_children ---');
}

function path_to_pidlist(path, poplast) {
  var pids = path.split('/');
  pids.shift();  // removing leading ""
  if (poplast) {
    pids.pop();
  }
  return pids;
}


// asynchronous version of editor_action: wait with javascript tree update until
// server has responded
function edit_action_sync(action, src, nodeids, add) {
    consoledb.groupCollapsed('edit_action_sync');
    consoledb.log('action: '+action+', src: '+src+', nodeids: '+nodeids+', add: '+add);
    var url = '&action='+escape(action);

    if (action=="move" || action=="copy"){
        url = '&action='+escape(action)+'&dest='+add;
    }

    var ajax_response; 

    var ctree = parent.getcoltree();
    var htree = parent.gethometree();
    
    if (src) {
        var src_node = htree.getNodeByKey(src);
        if (!src_node) {
            src_node = ctree.getNodeByKey(src);
        }
        if (src_node) {
            var src_node_title_old = src_node.title;
            src_node.setTitle(src_node_title_old + '<img height="30" src="/img/wait.gif" />');
        }
    }    

    var options = {
          url: '/edit/edit_action?srcnodeid='+src+'&style=popup'+url,
          async: false,
          dataType: 'json',
          type: 'POST',
          traditional: true, //"would POST param "id[]" with brackets in the name otherwise
          data: {ids: nodeids, csrf_token: parent.csrf},
          success: function (response) {
              ajax_response = response;
              new_path_endpoint = response.key;

              consoledb.log('edit_action_sync: $.ajax returns: '+response);
              consoledb.dir(response);

              if (src_node) {
                  // remove image wait.gif
                  src_node.setTitle(src_node_title_old);
                  src_node.render();
              }

              if ('changednodes' in ajax_response) {

                  var used_trees = [ctree, htree];

                  update_tree_nodes_labels(used_trees, ajax_response.changednodes);
              }
          },
        };

    $.ajax(options);
    consoledb.groupEnd('edit_action_sync');
    return ajax_response;
}

function setFolder(folderid)
{
    var src = tree.getFolder();
    if(action=="") {
        this.content.location.href = "edit_content?srcnodeid="+folderid+"&id="+folderid;
        this.buttons.location.href = "edit_buttons?id="+folderid;
    } else {
        edit_action(action, src, idselection, folderid);
        reloadPage(folderid, "");
    }
}

function activateEditorTreeNode(nid) {
  var ctree = parent.getcoltree();
  n = ctree.getNodeByKey(nid);
  if (n) {
      n.setActive();
      return;
  }
  var htree = parent.gethometree();
  var n = htree.getNodeByKey(nid);
  if (n) {
      n.setActive();
      return;
  }
}

function openWindow(fileName, width, height)
{
    win1 = window.open(fileName,'browsePopup','screenX=50,screenY=50,width='+width+',height='+height+',directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=no');
    win1.focus();
}

function reloadURL(url)
{
    this.location.href = url;
}

function getHelp(path){
    helpwindow = window.open(path,'browsePopup','width=600px,height=500px,directories=no,location=no,menubar=no,status=no,toolbar=no,resizable=yes');
    return false;
}

/* edit operations */
function doaction(checked) {
    console.log('list ' + checked);
    if(checked)
    {
        $('input[id^="check"]').each(function(){
            $(this).prop('checked', true);
        });
    }
    else
    {
        $('input[id^="check"]').each(function(){
            $(this).prop('checked', false);
        });
    }
}

function checkObject(field) {
    if(field.checked) {
        //check all objects with same field name because of two views
        $('input[name^='+field.name+']').each(function(){
            $(this).prop('checked', true);
        });
    } else {
        $('input[name^='+field.name+']').each(function(){
            $(this).prop('checked', false);
        });
    }
}


function modal_confirm(msg) {
  var string = '<div id="dialog-confirm" title="Empty the recycle bin?"><p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 20px 0;"></span>These items will be permanently deleted and cannot be recovered. Are you sure?</p></div>';
  var res = false;
  res = $(function() {
    var elem = $('<div/>').html(string);
    res = elem.dialog({
      resizable: false,
      height:140,
      modal: true,
      appendTo: "#mediatum_collectionstree",
      closeOnEscape: true,
      buttons: {
        "Delete all items": function() { res = true;
          $(this).dialog( "close" );

        },
        Cancel: function() { res = 7;
          $(this).dialog( "close" );

        }
      }
    });
  });
  return res;
}


function editSelected(nodeid){
    nodeid = nodeid ? [nodeid] : getAllObjectsNodeids();
    if (nodeid.length == 0) return;

    var form = $('<form action="/edit/edit_content" method="POST"></form>');
    form.append($('<input name="srcnodeid" value="' + parent.idselection + '" type="hidden">'));
    form.append($('<input name="tab" value="metadata" type="hidden">'));
    form.append($('<input name="csrf_token" value="' + parent.csrf + '" type="hidden">'));
    for (nid of nodeid)
        form.append($('<input name="ids" value="' + nid + '" type="hidden">'))
    $("body").append(form);
    form.submit();
}


function movecopySelected(action, nodeids){
    consoledb.groupCollapsed('movecopySelected');
    consoledb.log('movecopySelected: action '+action+'   nodeids: '+nodeids);
    consoledb.log('movecopySelected: getAllObjectsNodeids(): '+getAllObjectsNodeids());

    if (!nodeids) nodeids = getAllObjectsNodeids();

    parent.currentselection = nodeids;

    var confirm_msg = parent.$('#select_target_dir').text().replace(/\\n/g, '\n');
    parent.action = (nodeids.length > 0 && confirm(confirm_msg)) ? action : "";

    consoledb.log('parent.action:'+parent.action);
    consoledb.groupEnd('movecopySelected');
    return;
}


function deleteSelected(nodeids){
    if (!nodeids) nodeids = getAllObjectsNodeids();
    if (nodeids.length == 0) return;

    if(confirm($('#delete_text').text())) {
        edit_action_sync('delete', parent.last_activated_node.key, nodeids);
        reloadPage(parent.last_activated_node.key, '');
        try {
            parent.last_activated_node.load(forceReload=true);
        }
        catch(e) {
            consoledb.log('tried to reloadChildren() for node key='+
                          parent.last_activated_node.key+', title='+parent.last_activated_node.title+' caught: '+e);
        }
        return true;
    }
    return false;
}


function updateNodeLabels(ids) {
// pass ids as comma separated list
// the users trash, import, upload and faulty dirs will be update any case

  var ajax_response;
  
  var options = {
        url: '/edit/edit_action?action=getlabels&ids='+ids,
        async: false,
        dataType: 'json',
        success: function (response) {
            ajax_response = response;
            new_path_endpoint = response.key;

            consoledb.log('edit_action_sync: $.ajax returns: ', response);
            consoledb.dir(response);

            if ('changednodes' in ajax_response) {

                var ctree = parent.getcoltree();
                var htree = parent.gethometree();
                var used_trees = [ctree, htree];

                update_tree_nodes_labels(used_trees, ajax_response.changednodes);
            }
        },
      };

  $.ajax(options);
}


function sortItems_sync(o){

    var ajax_response;
    var options = {
          url: '/edit/edit_content?action=resort&srcnodeid='+id+'&id='+id+'&tab=content&value='+$(o).val(),
          async: false,
          dataType: 'json',
          success: function (data) {
              ajax_response = data;
              $('#scrollcontent').html(data.values);
          },
        };

    $.ajax(options);

}


function loadUrl(newLocation)
{
  window.location = newLocation;
  return false;
}


function sortItemsPage_sync(o1, o2, o3){


    var url
    if (o3 == '')
       url = '/edit/edit_content?srcnodeid='+id+'&id='+id+'&sortfield='+$(o1).val()+'&nodes_per_page='+$(o2).val();
    else
       url = '/edit/edit_content?srcnodeid='+id+'&id='+id+'&'+o3+'&sortfield='+$(o1).val()+'&nodes_per_page='+$(o2).val();
    reloadURL(url);
}


function saveSort(o){
    $.getJSON('/edit/edit_content?action=save&srcnodeid='+id+'&id='+id+'&tab=content&value='+$(o).val(), function(data) {
        // save done
        $("#message").html(data.message);
        $("#message").show().delay(5000).fadeOut();
    });
}


function saveSortPage(o1, o2){
    $.getJSON('/edit/edit_content?action=save&srcnodeid='+id+'&id='+id+'&tab=content&value='+$(o1).val()+'&nodes_per_page='+$(o2).val(), function(data) {
        // save done
        $("#message").html(data.message);
        $("#message").show().delay(5000).fadeOut();
    });
}


function getAllObjectsNodeids(){
    var s = [];
    $('input[id^="check"]:checked').each(function(){
        var nodeid = $(this).attr('id').substring(5);
        if (nodeid != 'node.id' & ! (s.includes(nodeid))){
            s.push(nodeid);
        }
    });
    return s;
}
