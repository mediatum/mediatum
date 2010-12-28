var lastmark = "";
var lasttime = 0;
    
function reloadPage()
{
    location.reload();
}

function openWindow(fileName)
{ 
    win1 = window.open(fileName,'imageWindow','screenX=50,screenY=50,width=800,height=800,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=yes'); 
    win1.focus();
} 

function openDetailWindow(fileName)
{ 
    win1 = window.open(fileName,'imageWindow','screenX=50,screenY=50,width=840,height=830,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizeable=yes'); 
    win1.focus();
} 
    
function fullSizePopup(id, width, height)
{
    url = '/fullsize?id='+id;

    if(screen.width>100 && screen.width-100 < width) {
        width = screen.width-100;
    }
    if(screen.height>100 && screen.height-100 < height) {
        height = screen.height-100;
    }

    var win1 = window.open(url,'image_fullsize','width='+width+',height='+height+',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=yes'); 
    win1.focus();
    return win1;
}

function shoppingbag(shoppingbag_width, shoppingbag_height)
{
    openPopup('/shoppingbag', 'bag', shoppingbag_width, shoppingbag_height, 'yes');
}

function shoppingBag(nodeid)
{
    var url = '/shoppingbag?files='+nodeid+'&action=add';
    x = http.open('get', url, true);
    http.send(null);
    http.onreadystatechange = function(){
        if(http.readyState==4){
            alert(unescape(http.responseText));
        }
    }
}

function addDirToShoppingBag(nodeid)
{
    openPopup('put_dir_into_shoppingbag?dir='+nodeid, 'move', 150,100, 'no');
}
   
function openPopup(url, name, width, height, scroll)
{
    var win1 = window.open(url,name,'width='+width+',height='+height+',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars='+scroll+',status=no,toolbar=no,resizable=yes'); 
    win1.focus();
    return win1;
}

/* extended search start */
function chg()
{
    document.xsearch.submittype.value = "change";
    document.xsearch.submit();
}

function clearFields()
{
    document.xsearch.field1.selectedIndex = 0;
    document.xsearch.field2.selectedIndex = 0;
    document.xsearch.field3.selectedIndex = 0;

    for (i=1; i<4; i++){
        obj = document.getElementById("query"+i);
        if (obj != null){
            if (obj.type == "text"){
                obj.value = "";
            }else if(obj.type == "select-one"){
                obj.selectedIndex = -1;
            }
        }
        obj = document.getElementById("query"+i+"-from");
        if (obj != null){
             obj.value = "";
             obj = document.getElementById("query"+i+"-to").value = "";
        }
    }
    chg();
}
/* extended search end */


function expandLongMetatext(id){
    document.getElementById(id+"_full").style.display = document.getElementById(id+"_full").style.display=='block'?'none':'block';
    document.getElementById(id+"_more").style.display = document.getElementById(id+"_full").style.display=='block'?'none':'block';
}

function questionDel(){
    return confirm(unescape("Soll dieser Eintrag wirklich gel%F6scht werden?"));
}


/* edit area */

function moveRight(left, right) {
        if (left.selectedIndex != -1) {
            for (i=left.length-1; i>=0; i--) {
                if (left.options[i].selected && left.options[i].value.charAt(0)!='{') {
                    mytext = left.options[i].text;
                    myvalue = left.options[i].value;
                    opt = new Option(mytext,myvalue);
                    right.options[right.length] = opt;
                    left.options[i]=null;
                }
            }
        }
    }

    function moveLeft(left, right) {
        if (right.selectedIndex!=-1) {
            for (i=right.length-1; i>=0; i--) {
                if (right.options[i].selected && right.options[i].value.charAt(0)!='{') {
                   mytext = right.options[i].text;
                   myvalue = right.options[i].value;
                   opt = new Option(mytext, myvalue);
                   left.options[left.length] = opt;
                   right.options[i]=null;
                }
            }
        }
    }

    function mark(list)
    {
        if (list){
            for (i=0; i<list.length; i++)
            {
                list.options[i].selected=true;
            }
        }
    }

function countMeta(obj, maxlength){
    if (maxlength==-1){
        return true;
    }
    
    n = document.getElementById('number'+obj.name);
    if (obj.value.length<maxlength){
        n.firstChild.data = maxlength-obj.value.length;
    }else{
        obj.value = obj.value.substring(0, maxlength);
        n.firstChild.data = maxlength-obj.value.length;
        return false;
    }
}

var http = createRequestObject();

function createRequestObject() {
    var tmpXmlHttpObject = null;
    try{
        tmpXmlHttpObject = new XMLHttpRequest();
    }                
    catch (ms){
        try{                        
            tmpXmlHttpObject = new ActiveXObject("Msxml2.XMLHTTP");
        }                     
        catch (nonms){
            try{                            
                tmpXmlHttpObject = new ActiveXObject("Microsoft.XMLHTTP");
            }                         
            catch (failed){
                tmpXmlHttpObject = null;
                alert("fail");
            }
        }
    }
    return tmpXmlHttpObject;
}

function handleArchived(nodeid, filename){
    var url = '/archive/'+nodeid+'/'+filename;
    obj = document.getElementById("object_highresolution_remark");

    if(obj){
        obj.style.display = 'inline';
    }
    
    x = http.open('get', url, true);
    http.send(null);
    http.onreadystatechange = function(){
        if(http.readyState==4){
            if(obj){
                obj.style.display = 'none';
            }
            return unescape(http.responseText);
        }
    }
}
