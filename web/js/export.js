function addscript(src) {
    document.write('<script src="' + src + '" type="text/javascript"' + '>' + '<' + '/script>');
}
function mediatum_load(id, limit, sort, query, format){
    document.write('<div id="mediatum">Loading...</div>');
    var url = "http://mediatum2.ub.tum.de/jssearch?id="+id;
    if(query) {
        url+="&q="+escape(query);
    }
    if(sort) {
        url+="&sort="+sort;
    }
    if(limit) {
        url+="&limit="+limit;
    }
    if(format){
        url+="&format="+format;
    }
    addscript(url);
}
var publication_class = null;
function add_data(data) {
    var d = document.getElementById("mediatum");
    var custom = 0;
    var style = "border: 1px solid #ccc; margin-bottom: 5px; font-size: 12px; "+
                "font-family: Arial,Geneva,sans-serif; color: #000";
    var styledata = "";
    if(publication_class) {
        styledata = "class=\""+publication_class+"\"";
    } else {
        styledata = "style=\""+style+"\"";
    }

    var s = ""
    for(i=0;i<data.length;i++)
    {
        if(custom) {
            node = data[i];
            s += node["author-contrib"] || '';
            s += ",";
            s += node["booktitle-contrib"] || '';
            s += ",";
            year = node["year"] || '0000';
            year = year.substring(0,4);
            s += year;
            s += "<br />";
        } else {
            s += '<a href="'+data[i]['link']+'" style="text-decoration: none"><div '+styledata+'>'
                           + '<b>' + (i+1) + " / " + data.length + "</b><br /><br />"
                           + data[i]['text']
                           + "<br />"
                           +"</div></a>";
        }
    }
    d.innerHTML = s;
}
