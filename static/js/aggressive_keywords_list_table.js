(function () {
    var tableInitialized = false;

    function categoryFormatter(cell) {
        if (!cell.getValue()) return "";
        var weight = cell.getRow().getData().weight || 0;
        var w = Math.min(1, Math.max(0, weight));
        var g = Math.round(255 * (1 - w));
        var color = "rgb(255," + g + ",0)";
        return "<span style='display:inline-block;width:12px;height:12px;border-radius:50%;background:" + color + ";'></span>";
    }

    document.getElementById('aggressive-keywords-list-tab').addEventListener('shown.bs.tab', function () {
        if (tableInitialized) return;
        tableInitialized = true;

        new Tabulator("#aggressiveKeywordsListTable", {
            ajaxURL: "/aggressive_keywords",
            layout: "fitDataTable",
            height: "300vh",
            initialSort: [{column: "word", dir: "asc"}],
            groupBy: "language",
            groupHeader: function (value, count) {
                return "Language: " + value.toUpperCase() +
                    "<span style='color:#d00; margin-left:10px;'>(" + count + " keywords)</span>";
            },
            columns: [
                {title: "Word", field: "word", hozAlign: "left", headerFilter: "input", width: 140},
                {title: "Weight", field: "weight", sorter: "number", hozAlign: "right"},
                {title: "Frequency", field: "frequency", sorter: "number", hozAlign: "right"},
                {title: "Diskrim", field: "category_diskrim", formatter: categoryFormatter, hozAlign: "center"},
                {title: "Lamuv", field: "category_lamuv", formatter: categoryFormatter, hozAlign: "center"},
                {title: "Netaisn", field: "category_netaisn", formatter: categoryFormatter, hozAlign: "center"},
                {title: "Aicin", field: "category_aicin", formatter: categoryFormatter, hozAlign: "center"},
                {title: "Darb", field: "category_darb", formatter: categoryFormatter, hozAlign: "center"},
                {title: "Pers", field: "category_pers", formatter: categoryFormatter, hozAlign: "center"},
                {title: "Asoc", field: "category_asoc", formatter: categoryFormatter, hozAlign: "center"},
                {title: "Milit", field: "category_milit", formatter: categoryFormatter, hozAlign: "center"},
                {title: "Nosod", field: "category_nosod", formatter: categoryFormatter, hozAlign: "center"},
                {title: "Emoc", field: "category_emoc", formatter: categoryFormatter, hozAlign: "center"},
                {title: "Nodev", field: "category_nodev", formatter: categoryFormatter, hozAlign: "center"},
            ],
        });
    });
})();
