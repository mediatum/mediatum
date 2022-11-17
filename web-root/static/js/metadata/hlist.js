/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

function sortOptions(options) {
    var optionsArray = $(options).toArray().sort(function (a, b) {
            x = a.innerHTML.toLowerCase();
            y = b.innerHTML.toLowerCase();
            return x < y ? -1 : x > y ? 1 : 0;
        });
    for (var i = 0; i <= options.length; i++) {
        options[i] = optionsArray[i];
    }
    options[0].selected = true;
}

$(function() {
    var options = {
        choose: ' ',
        empty_value: 'null',
        preselect: pre,
        indexed: true,
        set_value_on: 'each',
        on_each_change: '/metatype/hlist?attrfilter='+attrfilter,
        select_class: 'vertical',
        loading_image: '/static/img/loading.gif',
        attr: 'id'
    };
    var displayParents = function() {
        var labels = [];
        $(this).siblings().find(':selected').each(function() { labels.push($(this).val()); });
        $('input[name='+attrname+']').val(labels.join(';'));
    };

    $.getJSON('/metatype/hlist?attrfilter='+attrfilter, {id: startnode}, function(tree) {
        $('input[name='+attrname+']').optionTree(tree, options).change(displayParents);
        sortOptions($("select[name='"+ attrname + "_']").get(0).options);
    });
});
