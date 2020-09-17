/*
  Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
  SPDX-License-Identifier: AGPL-3.0-or-later
*/

$(function() {
    var options = {
        choose: ' ',
        empty_value: 'null',
        preselect: pre,
        indexed: true,
        set_value_on: 'each',
        on_each_change: '/metatype/hlist?attrfilter='+attrfilter,
        select_class: 'vertical',
        loading_image: '/img/loading.gif',
        attr: 'id'
    };
    var displayParents = function() {
        var labels = [];
        $(this).siblings().find(':selected').each(function() { labels.push($(this).val()); });
        $('input[name='+attrname+']').val(labels.join(';'));
    };

    $.getJSON('/metatype/hlist?attrfilter='+attrfilter, {id: startnode}, function(tree) {
        $('input[name='+attrname+']').optionTree(tree, options).change(displayParents);
    });
});
