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

function openPopup(url, name, width, height, scroll)
{
    var win1 = window.open(url,name,'width='+width+',height='+height+',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars='+scroll+',status=no,toolbar=no,resizable=yes');
    win1.focus();
    return win1;
}

/* extended search start */
function chg()
{
    var fieldno = $("*:focus").attr("name").substr(5,$("*:focus").attr("name").length-1)
    var sel_index = document.xsearch["field"+fieldno].selectedIndex;
    var searchmaskitem_id = document.xsearch["field"+fieldno][sel_index].value;
    var query_field_value = document.xsearch["query"+fieldno].value;
    var container_id = $("input[name=id]").val();

    $('#query'+fieldno).attr("disabled", true);

    $.getJSON("/node?jsoncallback=?",
    {
        jsonrequest: "True",
        cmd: "get_list_smi",
        fieldno: fieldno,
        searchmaskitem_id: searchmaskitem_id,
        container_id: container_id,
        query_field_value: query_field_value,
        format: "json"
    },
    function(data) {
        $('#query'+fieldno).replaceWith(data[0]);
        $('#query'+fieldno).removeAttr("disabled");
    })

}

function get_smi_id(fieldno)
{
    return document.xsearch["field"+fieldno].selectedIndex;
}

function clearFields()
{

    for (i=1; i<11; i++){
        if (( $("input[name=searchmode]").val() == "extended") && (i == 4)) {
            break;
        }
        document.xsearch["field"+i].selectedIndex = 0;
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
    document.xsearch.submittype.value = "change";
    document.xsearch.submit();
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
            if (left.options[i].selected && left.options[i].value!='__special_rule__') {
                mytext = left.options[i].text;
                myvalue = left.options[i].value;
                mytitle = left.options[i].title;
                opt = new Option(mytext,myvalue);
                opt.title = mytitle;
                right.options[right.length] = opt;
                left.options[i]=null;
            }
        }
    }
}

function moveLeft(left, right) {
    if (right.selectedIndex!=-1) {
        for (i=right.length-1; i>=0; i--) {
            if (right.options[i].selected && right.options[i].value!='__special_rule__') {
               mytext = right.options[i].text;
               myvalue = right.options[i].value;
               mytitle = right.options[i].title;
               opt = new Option(mytext, myvalue);
               opt.title = mytitle;
               left.options[left.length] = opt;
               right.options[i]=null;
            }
        }
    }
}

function mark(list){
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

function handleArchived(nodeid, filename){
    obj = $('#object_highresolution_remark');
    if(obj){
        obj.css('display', 'inline');
    }

    $.get('/archive/'+nodeid+'/'+filename, function(data) {
        if(obj){
            obj.css('display', 'none');
        }
        return unescape(data);
    });
}
