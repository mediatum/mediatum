function questionDelName(name){
    if (name==""){
    	return confirm(unescape("Soll dieser Eintrag wirklich gel%F6scht werden?"));
    }else{
        return confirm(unescape("Soll der Eintrag '"+name+"' wirklich gel%F6scht werden?"));
    }
}

function questionMoveUser(name){
    if (name==""){
    	return confirm(unescape("Soll dieser Benutzer wirklich zu den internen Benutzern verschoben werden?"));
    }else{
        return confirm(unescape("Soll der Benutzer '"+name+"' wirklich zu den internen Benutzern verschoben werden?"));
    }
}

function getEditRule(){
	if (document.getElementById("rule").value==""){
		return "";
	}else{
		return document.getElementById("rule").value;
	}
}

function getEditorValue(value){
	if (value != ""){
		document.getElementById("rule").value = value;
		document.getElementById("rule_show").innerHTML = value;
	}
	editor = null;
}


function setCancel(){
	document.getElementById("form_op").value = "cancel";
}

function metatypechange(doc){
	for(var i=0; i< doc.getElementById("mtype").options.length; i++){
		obj = doc.getElementById("div_" + doc.getElementById("mtype").options[i].value);
		
		if (obj){
			if (doc.getElementById("mtype").value == doc.getElementById("mtype").options[i].value){
				//obj.style.visibility = "visible";
				obj.style.display = "block";
			}else{
				obj.style.display = "none";
				//obj.style.visibility = "collapse ";
			}
		}
	}
}

function openSearchPopup(url, name, w, h){
    var win1 = window.open(url,name,'width='+w+',height='+h+',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=no'); 
    win1.focus();
    return win1;
}

function openPopup(url, name, w, h){
    var win1 = window.open(url,name,'width='+w+',height='+h+',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars=yes,status=no,toolbar=no,resizable=yes'); 
    win1.focus();
    return win1;
}

function openPopupWithScroll(url, name, w, h){
    var win1 = window.open(url,name,'width='+w+',height='+h+',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars=yes,status=no,toolbar=no,resizable=yes'); 
    win1.focus();
    return win1;
}


function nextWorkflowStep(op){
	document.getElementById('form_op').value=op;
}

function setWorkflow(){
	document.getElementById('form_op').value='addworkflow';
}

function moveOPup(obj){
	if (obj.selectedIndex >0){
		moveOP(obj, -1);
	}
}

function moveOPdown(obj){
	if (obj.selectedIndex<obj.length-1 && obj.selectedIndex!=-1){
		moveOP(obj, 1);
	}
}

function moveOP(obj, dir){
	selopt_text = obj.options[obj.selectedIndex].text;
	selopt_value = obj.options[obj.selectedIndex].value;

	obj.options[obj.selectedIndex].value = obj.options[obj.selectedIndex+dir].value
	obj.options[obj.selectedIndex].text = obj.options[obj.selectedIndex+dir].text;

	obj.options[obj.selectedIndex+dir].value = selopt_value;
	obj.options[obj.selectedIndex+dir].text = selopt_text;

	obj.selectedIndex = obj.selectedIndex+dir
}

function deleteOP(obj){
	if (obj.selectedIndex > -1){
		if (confirm(unescape("Soll diese Operation wirklich gel%F6scht werden?"))){
			obj.options[obj.selectedIndex] = null;
		}else{
			return false;
		}
	}
}

function selectAllOp(){
	obj = document.getElementById('ntruefunction');
	for (i=0;i<obj.length ; i++){
		obj.options[i].selected=true;
	}

	obj = document.getElementById('nfalsefunction');
	for (i=0;i<obj.length ; i++){
		obj.options[i].selected=true;
	}
	return false;
}

function setOpValue(){
	if (window.opener && !window.opener.closed){
		obj = window.opener.document.getElementById('ntruefunction');
		alert(obj.length);
		opt = new Option("abc","abc|");
		obj.options[obj.length] = opt;
		window.close();
	}
}

var import_page = 0

function show_import(doc, id, max){
	import_page = id
	for(var i=0; i<max; i++){
		obj = doc.getElementById("import" + i);

		if (obj){
			if (i==id){
				obj.style.visibility = "visible";
				obj.style.position="";
				obj.style.top = "300px";
			}else{
				obj.style.visibility = "hidden";
				obj.style.position="absolute";
			}
		}
	}
}

function show_import_next(doc, max){
	if (import_page<max-1){
		show_import(doc, import_page+1, max);
	}
}

function show_import_back(doc, max){
	if (import_page>1){
		show_import(doc, import_page-1, max);
	}
}

/*****/
var uploadfolderid=1;

function setUploadFolderID(id)
{
	uploadfolderid = id;
	alert(id);
}

function openWindow(fileName)
{ 
    win1 = window.open(fileName,'imageWindow','screenX=50,screenY=50,width=400,height=400,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=yes'); 
    //win1.focus();
}


function showPreview(doc, src){
	obj = doc.getElementById("image_preview");
	if (src!=""){
		obj.src = src;
	}else{
		obj.src = "/img/emtyDot1Pix.gif";
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


function buttonfix() {
    var buttons = document.getElementsByTagName('button');
    for (var i=0; i<buttons.length; i++) {
        if(buttons[i].onclick) continue;
        
        buttons[i].onclick = function () {
            for(j=0; j<this.form.elements.length; j++)
                if( this.form.elements[j].tagName == 'BUTTON' )
                    this.form.elements[j].disabled = true;
            this.disabled=false;
            this.value = this.attributes.getNamedItem("value").nodeValue ;
        }
    }
}

if (window.attachEvent) window.attachEvent("onload", IEhover);

window.onload = function() {
	linksExternal(); 
	defaultFocus();
 	if (document.getElementById('navt_tabs')) {
		var el = document.getElementById('navt_tabs');
		_add_show_handlers(el);
	}
 	if (document.getElementById('page_tabs')) {
		var el = document.getElementById('page_tabs');
		_add_show_handlers(el);
	}
}

function IEhover() {
		if (document.getElementById('nav')) {
			cssHover('nav','LI');	
		}
	 	if (document.getElementById('navt_tabs')) {
			cssHover('navt_tabs','DIV');
		}
	 	if (document.getElementById('page_tabs')) {
			cssHover('page_tabs','DIV');
		}
}

function cssHover(tagid,tagname) {
	var sfEls = document.getElementById(tagid).getElementsByTagName(tagname);
	for (var i=0; i<sfEls.length; i++) {
		sfEls[i].onmouseover=function() {
			this.className+=" cssHover";
		}
		sfEls[i].onmouseout=function() {
			this.className=this.className.replace(new RegExp(" cssHover\\b"), "");
		}
	}
}

function change(id, newClass, oldClass) {
	identity=document.getElementById(id);
	if (identity.className == oldClass) {
		identity.className=newClass;
	} else {
		identity.className=oldClass;
	}
}

function _add_show_handlers(navbar) {
    var tabs = navbar.getElementsByTagName('div');
    for (var i = 0; i < tabs.length; i += 1) {
	tabs[i].onmousedown = function() {
	    for (var j = 0; j < tabs.length; j += 1) {
		tabs[j].className = '';
		document.getElementById(tabs[j].id + "_c").style.display = 'none';
	    }
	    this.className = 'active';
	    document.getElementById(this.id + "_c").style.display = 'block';
	    return true;
	};
    }
    var activefound=0;
    for (var i = 0; i < tabs.length; i += 1) {
    	if (tabs[i].className=='active') activefound=i;
    }
    tabs[activefound].onmousedown();
}

function activatetab(index) {
	var el=0;
	if (document.getElementById('navt_tabs')) {
		el = document.getElementById('navt_tabs');
		
	} else {
 	  if (document.getElementById('page_tabs')) {
		  el = document.getElementById('page_tabs');
	  }
	}
	if (el==0) return;
	var tabs = navbar.getElementsByTagName('div');
	tabs[index].onmousedown();
}

function linksExternal()	{
	if (document.getElementsByTagName)	{
		var anchors = document.getElementsByTagName("a");
		for (var i=0; i<anchors.length; i++)	{
			var anchor = anchors[i];
			if (anchor.getAttribute("rel") == "external")	{
				anchor.target = "_blank";
			}
		}
	}
}

function defaultFocus() {

   if (!document.getElementsByTagName) {
        return;
   }

   var anchors = document.getElementsByTagName("input");
   for (var i=0; i<anchors.length; i++) {
      var anchor = anchors[i];
      var classvalue;

      //IE is broken! 
      if(navigator.appName == 'Microsoft Internet Explorer') {
            classvalue = anchor.getAttribute('className');
      } else {
            classvalue = anchor.getAttribute('class');
      }

      if (classvalue!=null) {
                var defaultfocuslocation = classvalue.indexOf("defaultfocus");
                if (defaultfocuslocation != -1) {
                	anchor.focus();
			var defaultfocusselect = classvalue.indexOf("selectall");
			if (defaultfocusselect != -1) {
				anchor.select();
			}
                }
        }
   }
}


