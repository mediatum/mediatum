/************************************************************************************************************
Static folder tree
Copyright (C) October 2005  DTHMLGoodies.com, Alf Magne Kalleland

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Dhtmlgoodies.com., hereby disclaims all copyright interest in this script
written by Alf Magne Kalleland.

Alf Magne Kalleland, 2006
Owner of DHTMLgoodies.com
    
************************************************************************************************************/    
    
/*
    Update log:
    December, 19th, 2005 - Version 1.1: Added support for several trees on a page(Alf Magne Kalleland)
    January,  25th, 2006 - Version 1.2: Added onclick event to text nodes.(Alf Magne Kalleland)
    February, 3rd 2006 - Dynamic load nodes by use of Ajax(Alf Magne Kalleland)
*/
        
    // helper variables
    var config = {};

    var ajaxObjectArray = new Array();
    var treeUlCounter = 0;
    
    var imageFolder = '/img/ftree/';    // Path to images
    var folderImage = 'folder.gif';
    var plusImage = 'plus.gif';
    var minusImage = 'minus.gif';
    var waitImage = 'spinner.gif';
    var checkImage = 'check.gif';
    var uncheckImage = 'uncheck.gif';
    
    var initExpandedNodes = '';    // Cookie - initially expanded nodes;

    var useAjaxToLoadNodesDynamically = true;
    var ajaxRequestFile = '/ftree/edittree';
    var contextMenuActive = false;    // Set to false if you don't want to be able to delete and add new nodes dynamically

    //var nodeId = 1;
    var startpath = new Array();

    
    /*
    These cookie functions are downloaded from 
    http://www.mach5.com/support/analyzer/manual/html/General/CookiesJavaScript.htm
    */
    function Get_Cookie(name) { 
       var start = document.cookie.indexOf(name+"="); 
       var len = start+name.length+1; 
       if ((!start) && (name != document.cookie.substring(0,name.length))) return null; 
       if (start == -1) return null; 
       var end = document.cookie.indexOf(";",len); 
       if (end == -1) end = document.cookie.length; 
       return unescape(document.cookie.substring(len,end)); 
    } 
    // This function has been slightly modified
    function Set_Cookie(name,value,expires,path,domain,secure) { 
        expires = expires * 60*60*24*1000;
        var today = new Date();
        var expires_date = new Date( today.getTime() + (expires) );
        var cookieString = name + "=" +escape(value) + 
           ( (expires) ? ";expires=" + expires_date.toGMTString() : "") + 
           ( (path) ? ";path=" + path : "") + 
           ( (domain) ? ";domain=" + domain : "") + 
           ( (secure) ? ";secure" : ""); 
        document.cookie = cookieString; 
    } 
    
    function expandAll(treeId)
    {
        var menuItems = document.getElementById(treeId).getElementsByTagName('LI');
        for(var no=0;no<menuItems.length;no++){
            var subItems = menuItems[no].getElementsByTagName('UL');
            if(subItems.length>0 && subItems[0].style.display!='block'){
                showHideNode(false,menuItems[no].id.replace(/[^0-9]/g,''));
            }            
        }
    }
    
    function collapseAll(treeId)
    {
        var menuItems = document.getElementById(treeId).getElementsByTagName('LI');
        for(var no=0;no<menuItems.length;no++){
            var subItems = menuItems[no].getElementsByTagName('UL');
            if(subItems.length>0 && subItems[0].style.display=='block'){
                showHideNode(false,menuItems[no].id.replace(/[^0-9]/g,''));
            }
        }        
    }
      
    function getNodePath(itemId)
    {
        $.get(ajaxRequestFile+'?pathTo='+itemId+'&style='+config['treeStyle']+"&multiselect="+config['multiselect'], function(data){
            initExpandedNodes = data;
            startpath = initExpandedNodes.split(",");
            if(initExpandedNodes){
                showHideNode(false, startpath[0]);
                startpath.splice(0,1);
                markFolder(false, currentfolder, currentfolder);
                    for (i=0;i<startpath.length-1;i++){
                        if (startpath[i]=='x'){
                            showHideNode(false,startpath[i+1]); 
                            startpath.splice(i, 1);
                        }
                    }
                    if(startpath.in_array('('+currentfolder+')')>=0){
                        markFolder(false, currentfolder, currentfolder);
                    } 
            }
            });
    }

    
    function parseSubItems(ulId,parentId)
    {
        if(initExpandedNodes){
            var nodes = initExpandedNodes.split(',');
        }
        var branchObj = document.getElementById(ulId);
        var menuItems = branchObj.getElementsByTagName('LI');    // Get an array of all menu items
        for(var no=0;no<menuItems.length;no++){
            var imgs = menuItems[no].getElementsByTagName('IMG');
            if(imgs.length>0)continue;
            var subItems = menuItems[no].getElementsByTagName('UL');
            var img = document.createElement('IMG');
            img.src = imageFolder + plusImage;
            img.onclick = showHideNode;
            if(subItems.length==0)img.style.visibility='hidden';else{
                subItems[0].id = 'tree_ul_' + treeUlCounter;
                treeUlCounter++;
            }
            var aTag = menuItems[no].getElementsByTagName('A')[0];
            //aTag.onclick = showHideNode;
            aTag.onclick = setFolder;
            menuItems[no].insertBefore(img,aTag);
            var folderImg = document.createElement('IMG');
            if(menuItems[no].className){
                folderImg.src = imageFolder + menuItems[no].className;
            }else{
                folderImg.src = imageFolder + folderImage;
            }
            menuItems[no].insertBefore(folderImg,aTag);
            
            var tmpParentId = menuItems[no].getAttribute('parentId');
            if(!tmpParentId)tmpParentId = menuItems[no].tmpParentId;
            if(tmpParentId && nodes[tmpParentId]){
                showHideNode(false,nodes[no]);
            }
            
            id = menuItems[no].id.replace("Node","");
            if (startpath.in_array(id)>=0){
                showHideNode(false, id);
                startpath.splice(startpath.in_array(id), 1);
            }else if(startpath.in_array('('+id+')')>=0){
                markFolder(false, id, id);
            }
        }
    }
        

    function showHideNode(e,inputId)
    {
        if(inputId){
            if(!document.getElementById('Node'+inputId))return true;
            thisNode = document.getElementById('Node'+inputId).getElementsByTagName('IMG')[0]; 
        }else {
            thisNode = this;
            if(this.tagName=='A')thisNode = this.parentNode.getElementsByTagName('IMG')[0];    
        }
        if(thisNode.style.visibility=='hidden')return;
        var parentNode = thisNode.parentNode;
        inputId = parentNode.id.replace(/[^0-9]/g,'');
        if(thisNode.src.indexOf(plusImage)>=0){
            thisNode.src = thisNode.src.replace(plusImage,minusImage);
            var ul = parentNode.getElementsByTagName('UL')[0];
            ul.style.display='block';
            if(!initExpandedNodes)initExpandedNodes = ',';
            if(initExpandedNodes.indexOf(',' + inputId + ',')<0) initExpandedNodes = initExpandedNodes + inputId + ',';
            
            if(useAjaxToLoadNodesDynamically){
                var firstLi = ul.getElementsByTagName('LI')[0];
                var parentId = firstLi.getAttribute('parentId');
                if(!parentId)parentId = firstLi.parentId;
                if(parentId){                   
                    $.get(ajaxRequestFile+'?parentId='+parentId+'&style='+config['treeStyle'], function(data){
                        document.getElementById(ul.id).innerHTML = data;
                        parseSubItems(ul.id, parentId);
                    });
                }
            }
            
        }else{
            thisNode.src = thisNode.src.replace(minusImage,plusImage);
            parentNode.getElementsByTagName('UL')[0].style.display='none';
            initExpandedNodes = initExpandedNodes.replace(',' + inputId,'');
        }
        if (e==false) window.scrollTo(0, thisNode.offsetTop);
        return false;
    }
    
    var okToCreateSubNode = true;
    
    function addNewNode(e)
    {
        if(!okToCreateSubNode)return;
        setTimeout('okToCreateSubNode=true',200);
        contextMenuObj.style.display='none';
        okToCreateSubNode = false;
        source = contextMenuSource;
        while(source.tagName.toLowerCase()!='li')source = source.parentNode;
        
    
        /*
        if (e.target) source = e.target;
            else if (e.srcElement) source = e.srcElement;
            if (source.nodeType == 3) // defeat Safari bug
                source = source.parentNode; */
        //while(source.tagName.toLowerCase()!='li')source = source.parentNode;
        var nameOfNewNode = prompt('Name of new node');
        if(!nameOfNewNode)return;

        uls = source.getElementsByTagName('UL');
        if(uls.length==0){
            var ul = document.createElement('UL');
            source.appendChild(ul);
            
        }else{
            ul = uls[0];
            ul.style.display='block';
        }
        var img = source.getElementsByTagName('IMG');
        img[0].style.visibility='visible';
        var li = document.createElement('LI');
        li.className='sheet.gif';
        var a = document.createElement('A');
        a.href = '#';
        a.innerHTML = nameOfNewNode;
        li.appendChild(a);
        ul.id = 'newNode' + Math.round(Math.random()*1000000);
        ul.appendChild(li);
        parseSubItems(ul.id);
        saveNewNode(nameOfNewNode,source.getElementsByTagName('A')[0].id);
        
    }
    
    /* Save a new node */
    function saveNewNode(nodeText,parentId)
    {
        self.status = 'Ready to save node ' + nodeText + ' which is a sub item of ' + parentId;
        // Use an ajax method here to save this new node. example below:
        /*
        $.get(ajaxRequestFile+'?newNode='+nodeText+'&parendId='+parentId, function(data){self.status = 'New node has been saved';});
        */
    }
    
    function deleteNode()
    {
        if(!okToCreateSubNode)return;        
        setTimeout('okToCreateSubNode=true',200);        
        contextMenuObj.style.display='none';
        source = contextMenuSource;
        
        if(!confirm('Click OK to delete the node ' + source.innerHTML))return;
        okToCreateSubNode = false;
        
        var parentLi = source.parentNode.parentNode.parentNode;
        while(source.tagName.toLowerCase()!='li')source = source.parentNode;        

        var lis = source.parentNode.getElementsByTagName('LI');
        source.parentNode.removeChild(source);
        if(lis.length==0)parentLi.getElementsByTagName('IMG')[0].style.visibility='hidden';
        deleteNodeOnServer(source.id);
    }
    
    function deleteNodeOnServer(nodeId)
    {
        self.status = 'Ready to delete node' + nodeId;
        // Use an ajax method here to save this new node. example below:
        /*
        $.get(ajaxRequestFile+'?deleteNodeId='+nodeId, function(data){self.status = 'Node has been deleted successfully';});
        */
        
    }
    
    function updateNodeLabel(nodeId)
    {
        $.get(ajaxRequestFile+'?getLabel='+nodeId+'&style='+config['treeStyle'], function(data){
                n_node = document.getElementById('Node'+nodeId);
                if(n_node){
                    t = n_node.getElementsByTagName('A')[0];
                    t.innerHTML = data;
                }
            });
    }
    
    function changeValue(nodeId)
    {
        markFolder(false,"", nodeId);
        $.get(ajaxRequestFile+'?changeCheck='+nodeId+'&currentitem='+currentitem, function(data){
                if(data){
                    alert(data);
                }
                parent.updateNodeLabels(nodeId);
            });
    }
    

    function markFolder(e,oldid, newid)
    {
        if (e){
            return false;
        }
        if(config['treeStyle']=='classification'){
            n_node = document.getElementById('Node'+newid);
            if (n_node){
                t = n_node.getElementsByTagName('A');
                
                if (t[0].style.backgroundColor=="" && t[0].className==""){
                    t[0].style.backgroundColor = "#ccc";
                    t[0].getElementsByTagName('input')[0].src = imageFolder + checkImage;
                    t[0].getElementsByTagName('input')[0].backgroundColor = "";
                    return false;
                }else{
                    t[0].style.backgroundColor = "";
                    t[0].getElementsByTagName('input')[0].src = imageFolder + uncheckImage;
                    t[0].getElementsByTagName('input')[0].backgroundColor = "";
                    return true;
                }
            }
            return false;
        }else{
            o_node = document.getElementById('Node'+oldid);
            if (o_node){
                t = o_node.getElementsByTagName('A');
                t[0].style.backgroundColor = "";
            }
            n_node = document.getElementById('Node'+newid);
            if(n_node){
                t = n_node.getElementsByTagName('A');
                t[0].style.backgroundColor = "#ccc";
            }
        }
        return false;
    }
    
    //function initTree(ids, style)
    function initTree(configuration)
    {
        idOfFolderTrees = configuration['idOfFolderTrees'];
        config['idOfFolderTrees'] = configuration['idOfFolderTrees'] || [];
        config['treeStyle'] = configuration['style'] || 'edittree';
        config['multiselect'] = configuration['multiselect'] || false;

        for(var treeCounter=0;treeCounter<config['idOfFolderTrees'].length;treeCounter++){
            var tree = document.getElementById(config['idOfFolderTrees'][treeCounter]);
            var menuItems = tree.getElementsByTagName('LI');    // Get an array of all menu items
            for(var no=0;no<menuItems.length;no++){                    
                var subItems = menuItems[no].getElementsByTagName('UL');
                var img = document.createElement('IMG');
                img.src = imageFolder + plusImage;
                img.onclick = showHideNode;
                if(subItems.length==0)img.style.visibility='hidden';else{
                    subItems[0].id = 'tree_ul_' + menuItems[no].id;
                }
                var aTag = menuItems[no].getElementsByTagName('A')[0];
                //aTag.onclick = showHideNode;
                aTag.onclick = setFolder;
                menuItems[no].insertBefore(img,aTag);
                var folderImg = document.createElement('IMG');
                if(menuItems[no].className){
                    folderImg.src = imageFolder + menuItems[no].className;
                }else{
                    folderImg.src = imageFolder + folderImage;
                }
                menuItems[no].insertBefore(folderImg,aTag);
            }
        }
        getNodePath(currentfolder);
    }
    
    
    Array.prototype.in_array = function(needle){
        for(var i=0; i<this.length; i++){
            if(needle===this[i])
                return i;
        }
        return  -1;
    }
  