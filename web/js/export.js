var mediatum_config = {};
var mediatum_config_default = {'fields':['<b>[att:pos]</b>','defaultexport'], 'divider':'<br/>', 'target':'internal', 'output':'default', 'groupby':''};
var module_count = 0;
var baseurl = getLocation();
var styledone = 0;

var labels = {'de':['lade...', 'Suche', 'Suche nach:', 'Treffer'],
                'en':['loading...', 'search', 'Search term:', 'matches']};


var load_script = function(options) {
    options.owner_document = options.owner_document || document;
    
    var script_tag = options.owner_document.createElement('script');
    script_tag.setAttribute('type', 'text/javascript');
    script_tag.setAttribute('src', options.src);
    script_tag.onload = function() {
        script_tag.onreadystatechange = null;
        options.callback && options.callback(options.position);  
    };  
    
    script_tag.onreadystatechange = function() {
        if (script_tag.readyState == 'loaded' || script_tag.readyState == 'complete') {
            script_tag.onload = null;
            options.callback && options.callback(options.position);
        }  
    };
    options.owner_document.getElementsByTagName('head')[0].appendChild(script_tag);
};

function getLocation(){
    objs = document.getElementsByTagName('script');
    for (var i in objs){
        if (objs[i].src && objs[i].src.indexOf("export.js")>0){
            return(objs[i].src.replace("/js/export.js", ""));
        }
    }
    return "";
}

function pad(number, length) {
    var str = '' + number;
    while (str.length < length) {
        str = '0' + str;
    }
    return str;
}

function mediatum_load(id, limit, sort, query, format, language, type, detailof){
    if(language==""){
        document.write('<div class="mediatum" id="mediatum_'+module_count+'"><p class="loading"><img src="'+baseurl+'/img/wait_small.gif"/></p></div>');
    }else{
        document.write('<div class="mediatum" id="mediatum_'+module_count+'"><p class="loading">'+labels[language][0]+'</p></div>');
        language = language;
    }

    load_script({ 
        src: 'http://mediatum.ub.tum.de/js/jquery.min.js',
        position: module_count,
        callback: function(pos) {
            
            if(detailof || detailof==0){
                var divider = mediatum_config['divider'+detailof] ? mediatum_config['divider'+detailof] : mediatum_config_default.divider;
                var fields = mediatum_config['fields'+detailof] ? mediatum_config['fields'+detailof] : mediatum_config_default.fields;
                var target = mediatum_config['target'+detailof] ? mediatum_config['target'+detailof] : mediatum_config_default.target;
            }else{
                var divider = mediatum_config['divider'+pos] ? mediatum_config['divider'+pos] : mediatum_config_default.divider;
                var fields = mediatum_config['fields'+pos] ? mediatum_config['fields'+pos] : mediatum_config_default.fields;
                var target = mediatum_config['target'+pos] ? mediatum_config['target'+pos] : mediatum_config_default.target;
            }
            var type = mediatum_config['type'+pos] ? mediatum_config['type'+pos] : ['','search', ''];
            var output = mediatum_config['output'] ? mediatum_config['output'] : mediatum_config_default.output;
            var groupby = mediatum_config['groupby'] ? mediatum_config['groupby'] : mediatum_config_default.groupby;
            if (output!='default'){
                fields = new Array('defaultexport');
            }
            
            if (type[0]=='struct'){
                var url = baseurl+"/services/export/node/"+id+"/children?format=json&type=.*(directory|collection).*";
            }else{
                var url = baseurl+"/services/export/node/"+id+"/allchildren?format=json&type=.*(document|diss|image|video).*";
            }
            
            var file = true;
            if (mediatum_config['fields'+pos]){
                file = /!hasfile*/.test(mediatum_config['fields'+pos].join(""));
            }
            if (mediatum_config['fields'+detailof]){
                file = /hasfile*/.test(mediatum_config['fields'+detailof].join("")); 
            }
            if (file){
                url += "&files=all";
            }

            url += query ? "&q="+escape(query) : "";
            url += "&sortfield="+sort
            url += limit ? "&limit="+limit : "";
            url += format ? "&format="+format : "";
            url += language ? "&lang="+language : "";
            //url += "&acceptcached=180&mask=default&type=.*(document|diss|image|video).*";
            url += "&acceptcached=180&mask="+output;
            url += (mediatum_config['fields'+pos] || mediatum_config['fields'+detailof]) ? "&attrspec=all" : "";
            if ((mediatum_config['style'] ? mediatum_config['style']:1)==1 && styledone==0){
                $('<style>\n.mediatum #item{padding:2px; margin:2px; border: 1px solid silver;}\n.mediatum #item_link{text-decoration:none; color:black;}\n</style>').appendTo('body');
                styledone = 1;
            }

            $.getJSON(url+"&jsoncallback=?",
                function(data){
                    if (type[0]=='struct'){
                        $('<div id="navigation_'+pos+'" class="navigation"> </div><div><div id="content_'+pos+'" class="content"><div id="searchresult_'+pos+'" class="searchresult"> </div></div>').appendTo("#mediatum_"+pos);
                        buildNavigation(id, limit, sort, query, format, language, type, pos);
                        return;
                    }
                    if (target=="external"){
                        target = ' target=\'_blank\'';
                    }else{
                        target = '';
                    }

                    _group = '';
                    _groupfunc = '';
                    if(groupby.match(/(\|.*)/g)){
                        _groupfunc = groupby.replace(/(.*)\|/, '');
                        groupby = groupby.replace(/(\|.*)/g,'');
                    }

                    $.each(data.nodelist, function(i,item){
                        var x = "";
                        var s = "";

                        if(groupby!=''){ // group by given attribute and build div
                            if(item[0].attributes[groupby]!=_group){
                                _v = formatData('[att:'+groupby+'|'+_groupfunc+']', item, 0 );
                                if(_v!=''){
                                    s += '<p id="groupby_header">'+_v+'</p>';
                                    _group = item[0].attributes[groupby];
                                }
                            }
                        }

                        s += '<a href="'+baseurl+'/?id='+item[0].id+'"'+target+' id="item_link"><div id="item">'
                        $.each(fields, function(index, value){
                            d = 0;
                                try{
                                    d = formatData(value, item, i, data.nodelist.length);
                                    s += d;
                                    if (fields[fields.length-1]!=value && d.length>0){
                                        s += divider;
                                    }
                                }catch(e){
                                    //do nothing
                                }
                           });
                        s+= "</div></a>";
                        if($('#mediatum_'+detailof+'_'+id).length>0){
                            $(s).appendTo('#mediatum_'+detailof+'_'+id);
                        }else{
                            $(s).appendTo("#mediatum_"+pos);
                        }
                    });
                    $("p").remove(".loading");
                }
            );
        }
    });
    module_count += 1;
}

function show(pos, id){
    $("#searchresult_"+pos).css("display", "none");
    $(".part_"+pos).css("display", "none");
    $("#mediatum_"+pos+"_"+id).css("display", "block");
    return false;
}

function startsearch(pos, baseid, language){
    $("#searchresult_"+pos).html('<img src="'+baseurl+'/img/wait_small.gif"/>');
    $(".part_"+pos).css("display", "none");
    $("#searchresult_"+pos).css("display", "block");

    var fields = mediatum_config['fields'+pos] ? mediatum_config['fields'+pos] : mediatum_config_default.fields;
    var divider = mediatum_config['divider'+pos] ? mediatum_config['divider'+pos] : mediatum_config_default.divider;
    var target = mediatum_config['target'+pos] ? mediatum_config['target'+pos] : mediatum_config_default.target;
    
    url = baseurl+"/services/export/node/"+baseid+"/allchildren?sortfield=-node.name&type=.*(document|diss|image|video).*&format=json&mask=default&q=full="+ $('#searchterm_'+pos).val();
    url += (mediatum_config['fields'+pos] || mediatum_config['fields'+detailof]) ? "&attrspec=all" : "";

    $.getJSON(url+"&jsoncallback=?", function(data){
        $("#searchresult_"+pos).html('<p class="search">'+labels[language][2]+' \''+$('#searchterm_'+pos).val()+'\' ('+data.nodelist.length+' '+labels[language][3]+')</p>');
        s = '';
        $.each(data.nodelist, function(i,item){
            s += '<a href="'+baseurl+'/?id='+item[0].id+'"'+target+' id="item_link"><div id="item">'
            $.each(fields, function(index, value){
            d = 0;
                try{
                    d = formatData(value, item, i, data.nodelist.length);
                    s += d;
                    if (fields[fields.length-1]!=value && d.length>0){
                        s += divider;
                    }
                 }catch(e){
                    // do nothing
                }
            });
            s += '</div></a>';
        });
        $(s).appendTo("#searchresult_"+pos);
    });
}


function buildNavigation(id, limit, sort, query, format, language, type, pos){
    s = '';
    var first = -1;
    sortdir = type[2]=='asc' ? '' : '-';
    $.getJSON(baseurl+'/services/export/node/'+id+'/children?sortfield='+sortdir+'node.name&type=.*(directory|collection).*&format=json&jsoncallback=?', function(data){
        var links = new Array();
        var fields = mediatum_config['fields'+pos] ? mediatum_config['fields'+pos] : mediatum_config_default.fields;
        $.each(data.nodelist, function(i,item){
            links.push('<a href="#" onclick="return show('+pos+','+item[0]['id']+')">'+item[0]['attributes']['nodename']+'</a> ');
            $('#content_'+pos).append('<div id="mediatum_'+pos+"_"+item[0]['id']+'" class="mediatum part_'+pos+'" title="part_'+pos+'"></div>');
            mediatum_load(item[0]['id'], limit, sort, query, format, language, type, pos);
            if (first==-1){
                first = item[0]['id'];
            }
        });
        show(pos, first);
        if(type[1]=='search'){
            links.push('<input type="text" name="searchterm" id="searchterm_'+pos+'"/><button type="button" onclick="startsearch('+pos+', '+id+', \''+language+'\')">'+labels[language][1]+'</button>');
        }
        $("#navigation_"+pos).append(links.join(' | '));
    });
}

var z = 0;

function formatData(value, item, i, l){
    var val;
    var result;
    var re = new RegExp("\[att\:[\\.\\,\\\\;\\\\s\\\\&|A-Za-z0-9_-]*\]");
    
    func = "";
    while(result = re.exec(value)!=null){ // replace all attributes
        val = re.exec(value);
        attrname = val[0].replace(/(\[att:)|(\])/g, '');
        //attrname = attrname.replace(/(\|.*)/g, '');

        if(attrname.match(/(\|.*)/g)){
            func = attrname.replace(/(.*)\|/, '');
            attrname = attrname.replace(/(\|.*)/g,'');
        }
        
        if(value.match(/(\[att:id\])/g)){ // id
            value = value.replace(/(\[att:id\])/g, item[0].id);
        }
        else if(value.match(/(\[att:pos\])/g)){ // pos
            value = value.replace(/(\[att:pos\])/g, (i+1) + "/" + l);
        }
        else if(item[0]['attributes'][attrname] && item[0]['attributes'][attrname]!=""){ // test attributes
            value = value.replace(val, execFuncts(item[0]['attributes'][attrname], func));
            //value = value.replace(val, item[0]['attributes'][attrname]);
            
        }else{ // attribute not found
            value = "";
        }
        
        func = "";
    }
    

    
    if ((new RegExp(/(defaultexport)/g)).exec(value)){ // defaultexport
        value = item[0]['defaultexport'];
    }
    
    if ((new RegExp(/(\|hasfile)/g)).exec(value)){ // test of existing file
        value = value.replace(/(\|hasfile)/g, '');
        if ((item[0]['files'].length)==0){
            value = "";
        }
    }

    return value;
}

function execFuncts(value, func){
    if (func==""){
        return value;
    }

    if ((new RegExp(/(substring:)/g)).exec(func)){ // substring -> syntax: |substring:start,end
        format = func.replace(/(substring:)/g, "").split(",");
        if (format.length==2){
            if (value.substring(format[0]-1, format[1])){
                return value.replace(value, value.substring(format[0]-1, format[1]));
            }else{
                return "";
            }
        }else{
            return "";
        }
    }
    
    /*if ((new RegExp(/(replace:)/g)).exec(func)){ // replace -> syntax: |replace:pattern,replace
        //format = func.replace(/(replace:)/, "").split("|")[0].split(",");
        format = func.replace(/(replace:)/, "").split("|")[0].split(/([^\,]*),(.*)/g);
        if (format.length==4){
            return value.replace(new RegExp(format[1],"g"), format[2]);  
        }
    }*/
    if ((new RegExp(/(replace:)/g)).exec(func)){ // replace -> syntax: |replace:pattern,replace
        format = func.replace(/(replace:)/, "").split("|")[0];
        var a = format.split(/([^\,]*),(.*)/g);
        if (a.length==4){
            return value.replace(new RegExp(a[1],"g"), a[2]);  
        }else{
            a = format.split(',');
            return value.replace(new RegExp(a[0],"g"), a[2]);  
        }
    }
    
    if ((new RegExp(/(splitstring:)/g)).exec(func)){ // splitstring -> syntax: |splitstring:pattern,position
        format = func.replace(/(splitstring:)/, "").split("|")[0].split(",");
        if (format.length==2){
            if (value.split(format[0])[format[1]]){
                return value.replace(value, value.split(format[0])[format[1]]);
            }   
        }
    }
    
    if ((new RegExp(/(formatdate:)/g)).exec(func)){ // date format -> syntax: |formatdate:[Y|M|D|h|m|s]*
        format = func.replace(/(formatdate:)/g, "");
        d = new Date(Date.parse(value.replace(/(\-)/g,"/"), 'YYYY/MM/DDThh:mm:ss'));
        format = format.replace("Y", d.getFullYear());
        format = format.replace("M", pad(d.getMonth(), 2));
        format = format.replace("D", pad(d.getDate(), 2));
        format = format.replace("h", pad(d.getHours(), 2));
        format = format.replace("m", pad(d.getMinutes(), 2));
        format = format.replace("s", pad(d.getSeconds(), 2));
        return value.replace(value, format).replace(/\formatdate:.*/g, "");
    }

}
