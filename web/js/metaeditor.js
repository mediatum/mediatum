var i = 0;
var selected = false;
var sellist = "";
var spanid = 0;

function pick(obj){
    if (selected==false){
        i++;
        if (i==1){
           if (!isSelected(obj)){
                obj.style.border = "solid silver 1px";
                obj.style.backgroundColor = "#dcdcdc";
                spanid=obj.id;
                sub = document.getElementById(obj.id+"_sub");
                if (sub){
                    sub.style.display='block';
                }
            }
        }
    }   
}

function unpick(obj){
    if (selected==false){
        if (isSelected(obj)){
           return;
        }
        obj.style.border = "solid white 1px";
        obj.style.backgroundColor = "";
        i=0;
        spanid = 0;
        sub = document.getElementById(obj.id+"_sub");
        if (sub){        
            sub.style.display='none';
        }
    }
}

function select(obj){
    if (!isSelected(obj)){
        sellist += obj.id+";";
        obj.style.border = "solid red 1px";
        obj.style.backgroundColor = "#FFE7E7";
    }else{
        sellist = sellist.replace(obj.id+";","");
        unpick(obj);
    }
    var div = document.getElementById("selection_div");
    if(div){
        if (sellist.length>0){
            div.style.display= 'block';
        }else{
            div.style.display= 'none';
        }
    }
}

function isSelected(obj){
    if (sellist == sellist.replace(obj.id+";","")){
        return false;
    }else{
        return true;
    }
}

function getSellist(){
    document.getElementById("sel_id").value=sellist;
}

function questionDel(){
    return confirm(unescape("Soll dieser Eintrag wirklich gel%F6scht werden?"));
}


function moveRight(left, right) {
    if (left.selectedIndex != -1) {
        for (i=left.length-1; i>=0; i--) {
            if (left.options[i].selected && left.options[i].value!='__special_rule__') {
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
            if (right.options[i].selected && right.options[i].value!='__special_rule__') {
               mytext = right.options[i].text;
               myvalue = right.options[i].value;
               opt = new Option(mytext, myvalue);
               left.options[left.length] = opt;
               right.options[i]=null;
            }
        }
    }
}

function mark(list){
    for (i=0; i<list.length; i++)
    {
        list.options[i].selected=true;
    }
}

function setCancel(obj){
    obj.value="cancel";
}

function openPopup(url, name, width, height){
    var win1 = window.open(url,name,'width='+width+',height='+height+',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=yes'); 
    win1.focus();
    return win1;
}


function metatypechange(doc){
    for(var i=0; i< doc.getElementById("newfieldtype").options.length; i++){
        obj = doc.getElementById("div_" + doc.getElementById("newfieldtype").options[i].value);
        if (obj){
            if (doc.getElementById("newfieldtype").value == doc.getElementById("newfieldtype").options[i].value){
                obj.style.display = "block";
                
            }else{
                obj.style.display = "none";
            }
        }
    }
}

function getTypeString(s){ 
    return s.substring(s.lastIndexOf('(')+1,s.length-1);
}

function editmetatypechange(doc){
    seltype = getTypeString(doc.getElementById("newfieldtype").options[doc.getElementById("newfieldtype").selectedIndex].text);
    for(var i=0; i< doc.getElementById("newfieldtype").options.length; i++){
        obj = doc.getElementById("div_" + getTypeString(doc.getElementById("newfieldtype").options[i].text));
        if (obj){
            obj.style.display = "none";
        }
    }
    if (doc.getElementById("div_"+seltype)){
        doc.getElementById("div_"+seltype).style.display = "block";
    }
}


function showPreview(doc, src){
    obj = doc.getElementById("image_preview");
    if (src!=""){
        obj.src = src;
    }else{
        obj.src = "/img/emtyDot1Pix.gif";
    }
}

function countMeta(obj, l){
    /*dummy method*/
}

function show_testnodes() {
  
  var wn = window.open("", "popup", "resizable=1,width=700,height=450,scrollbars");
  var wndoc = wn.document;
  
  var post_action = (""+window.location).split('?')[0]+'/show_testnodes?style=popup';
  
  wndoc.write("rendering test nodes ..."); // text node needed for Firefox
  wndoc.write('<form id="iframe_form01" method="POST" action="'+post_action+'"/>');
  wndoc.write('<input id="iframe_input_template" type="hidden" name="template"/>');
  wndoc.write('<input id="iframe_input_testnodes" type="hidden" name="testnodes"/>');
  wndoc.write('<input id="iframe_input_item_id" type="hidden" name="item_id"/>');
  wndoc.write('<input id="iframe_input_width" type="hidden" name="width"/>');
  
  wndoc.getElementById('iframe_input_template').value = document.getElementById('textarea_template').value;      
  wndoc.getElementById('iframe_input_testnodes').value = document.getElementById('input_testnodes').value;      
  wndoc.getElementById('iframe_input_item_id').value = document.getElementById('item_id').value;;      
  wndoc.getElementById('iframe_input_width').value = document.getElementById('input_width').value;      
  
  wndoc.getElementById('iframe_form01').submit();
  
}

