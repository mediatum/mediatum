function addscript(src) {
    document.write('<script src="' + src + '" type="text/javascript"' + '>' + '<' + '/script>');
}
function mediatum_load(id,author){
    document.write('<div id="mediatum">Loading...</div>');
    var url = "http://mediatum2.ub.tum.de/jssearch?id="+id;
    if(author) {
        url+="&q="+escape("author="+author);
    }
    addscript(url);
}
var publication_class = null;
function add_data(data) {
    var d = document.getElementById("mediatum");
    var custom = 0;
    d.innerHTML = "";
    var style = "border: 1px solid #ccc; margin-bottom: 5px; font-size: 12px; "+
                "font-family: Arial,Geneva,sans-serif; color: #000";
    var styledata = "";
    if(publication_class) {
        styledata = "class=\""+publication_class+"\"";
    } else {
        styledata = "style=\""+style+"\"";
    }

    for(i=0;i<data.length;i++)
    {
        if(custom) {
            node = data[i];
            d.innerHTML += node["author-contrib"] || '';
            d.innerHTML += ",";
            d.innerHTML += node["booktitle-contrib"] || '';
            d.innerHTML += ",";
            year = node["year"] || '0000';
            year = year.substring(0,4);
            d.innerHTML += year;
            d.innerHTML += "<br />";
        } else {
            d.innerHTML += '<a href="'+data[i]['link']+'" style="text-decoration: none"><div '+styledata+'>'
                           + '<b>' + (i+1) + " / " + data.length + "</b><br /><br />"
                           + data[i]['text']
                           + "<br />"
                           +"</div></a>";
        }
    }
}
