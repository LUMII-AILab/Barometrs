function createAggressiveKeywordsTable() {
    var table = new Tabulator("#aggressiveKeywordsTable", {
        ajaxURL: "/aggressive_keywords_by_day",
        ajaxParams: function() {
            const form = $('#analysisRequestForm');
            return {
                requestDate: form.find('[name="requestDate"]').val(),
                language: form.find('[name="language"]').val(),
            };
        },
        width: 300,
        height: 800,
        layout: "fitColumns",
        initialSort: [{column: "count", dir: "desc"}],
        groupBy: function(data) {
            return data.language;
        },
        groupHeader: function(value, count) {
            return "Language: " + value.toUpperCase() + "<span style='color:#d00; margin-left:10px;'>(" + count + " keywords)</span>";
        },
        columns: [
            {title: "Keyword", field: "word", hozAlign: "left", headerFilter: "input"},
            {title: "Count", field: "count", sorter: "number", formatter: cell => cell.getValue(), hozAlign: "left", width: 80},
        ],
    });
}
