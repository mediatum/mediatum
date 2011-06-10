var mediatum_config = {};
var mediatum_config_default = {'fields':['<b>[att:pos]</b>','defaultexport'], 'divider':'<br/>', 'target':'internal'};
var module_count = 0;

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


function mediatum_load(id, limit, sort, query, format, language){
    baseurl = getLocation();
    
    if(language==""){
        document.write('<div class="mediatum" id="mediatum_'+module_count+'"><p class="loading"><img src="'+baseurl+'/img/wait_small.gif"/></p></div>');
    }else if(language=="de"){
        document.write('<div class="mediatum" id="mediatum_'+module_count+'"><p class="loading">lade...</p></div>');
    }else{
        document.write('<div class="mediatum" id="mediatum_'+module_count+'"><p class="loading">loading...</p></div>');
    }
    
    load_script({ 
        src: 'http://code.jquery.com/jquery-latest.js',
        position: module_count,
        callback: function(pos) { 
            var url = baseurl+"/services/export/node/"+id+"/allchildren?format=json";
            
            url += query ? "&q="+escape(query) : "";
            url += (sort.substring(0,1)=="-") ? "&sortfield="+sort.substring(1)+"&sortdirection=down" : "&sortfield="+sort
            url += limit ? "&limit="+limit : "";
            url += format ? "&format="+format : "";
            url += language ? "&lang="+language : "";
            url += "&type=.*(document|diss).*";
            
            
            style = mediatum_config['style'] ? mediatum_config['style'] : 1;
            if (style==1){
                s = '<style>\n.mediatum #item{padding:2px; margin:2px; border: 1px solid silver;}\n.mediatum #item_link{text-decoration:none; color:black;}\n</style>';
                $(s).appendTo('body');
            }

            $.getJSON(url+"&jsoncallback=?",
                function(data){
                    divider = mediatum_config['divider'+pos] ? mediatum_config['divider'+pos] : mediatum_config_default.divider;
                    fields = mediatum_config['fields'+pos] ? mediatum_config['fields'+pos] : mediatum_config_default.fields;
                    target = mediatum_config['target'+pos] ? mediatum_config['target'+pos] : mediatum_config_default.target;
                    
                    if (target=="external"){
                        target = ' target=\'_blank\'';
                    }else{
                        target = '';
                    }
                    $.each(data.nodelist, function(i,item){
                        s = '<a href="'+baseurl+'/?id='+item[0].id+'"'+target+' id="item_link"><div id="item">'
                            $.each(fields, function(index, value){
                                try{
                                    val = value.replace(/(.*att:)|(].*)/g, "");
                             
                                    if (val.replace(/(.*\|formatdate:)/g, "")!=val){ //date
                                        format = val.replace(/(.*\|formatdate:)/g, "")
                                        v = val.replace(/(\|formatdate.*)/g, "");
                                        d = new Date(Date.parse(item[0]['attributes'][v]));
                                        format = format.replace("Y", d.getFullYear());
                                        format = format.replace("M", pad(d.getMonth(), 2));
                                        format = format.replace("D", pad(d.getDate(), 2));
                                        format = format.replace("h", pad(d.getHours(), 2));
                                        format = format.replace("m", pad(d.getMinutes(), 2));
                                        format = format.replace("s", pad(d.getSeconds(), 2));
                                        s += value.replace("[att:"+val+"]", format);
                                    
                                    } else if (val.replace(/(.*\|substring:)/g, "")!=val){
                                        format = val.replace(/(.*\|substring:)/g, "").split(",");
                                        if (format.length==2){
                                            v = item[0]['attributes'][val.replace(/(\|substring:.*)/g, "")];
                                            if (v.substring(format[0], format[1])){
                                                s += value.replace("[att:"+val+"]", v.substring(format[0], format[1]));
                                            }
                                        }
                                    
                                    } else if (val.replace(/(.*\|splitstring:)/g, "")!=val){
                                        format = val.replace(/(.*\|splitstring:)/g, "").split(",");
                                        if (format.length==2){
                                            v = item[0]['attributes'][val.replace(/(\|splitstring:.*)/g, "")];
                                            if (v.split(format[0])[format[1]]){
                                                s += value.replace("[att:"+val+"]", v.split(format[0])[format[1]]);
                                            }
                                        }

                                    }else if(val=='pos'){
                                        s += value.replace("[att:"+val+"]", (i+1) + "/" + data.nodelist.length);
                                    }else if (value==val && item[0][val]){
                                        s += value.replace(val, item[0][val]);    
                                    }else if (value.indexOf("[att:"+val+"]")!=-1){
                                        d_val = item[0]['attributes'][val];
                                        if (d_val){ // attribute found
                                            s += value.replace("[att:"+val+"]", d_val);
                                        }
                                    }else{
                                        s+=value;
                                    }
                                    
                                    if (fields[fields.length-1]!=value){
                                        s += divider;
                                    }
                                }catch(e){
                                    // do nothing
                                }
                           });
                        s+= "</div></a>";
                        $(s).appendTo("#mediatum_"+pos);
                    });
                    $("p").remove(".loading");
                }
            );
        }
    });
    module_count += 1;
}
