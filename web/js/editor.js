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
    var url = '/edit/edit_content?id='+nodeid;
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
    
    $.get('/edit/edit_action?src='+src+'&ids='+ids+'&style=popup'+url, function(data){
        if (data!=""){
            if(add==1 || add==2){
                parent.tree.location.href = "/edit/edit_tree?id="+data;
            }
            parent.content.location.href = "/edit/edit_content?id="+data;
        }
    });
}


function setFolder(folderid)
{
    var src = tree.getFolder();
    if(action=="") {
        this.content.location.href = "edit_content?id="+folderid;
        this.buttons.location.href = "edit_buttons?id="+folderid;
    } else {
        edit_action(action, src, idselection, folderid);
        reloadPage(folderid, "");
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



