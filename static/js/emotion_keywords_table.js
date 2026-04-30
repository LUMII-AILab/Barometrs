function createEmotionKeywordsTable() {
    var table = new Tabulator("#emotionKeywordsTable", {
        ajaxURL: "/predicted_comments_emotion_keywords",
        ajaxParams: function(){
            const form = $('#analysisRequestForm');

            return {
                predictionType: form.find('[name="currentPredictionType"]').val(),
                requestDate: form.find('[name="requestDate"]').val(),
                language: form.find('[name="language"]').val(),
            }
        },
        height: 1000,
        layout: "fitColumns",
        groupBy: function(data){
            return data.emotion;
        },
        groupHeader: function(value, count, data, group){
            return "Emotion: " + value;
        },
        columns: [
            {
                title: "Keyword",
                field: "keyword",
                hozAlign: "left",
                headerFilter: "input",
            },
            {
                title: "Score (%)",
                field: "confidence",
                width: 100,
                formatter: cell => (cell.getValue() * 100).toFixed(2) + "%",
                hozAlign: "left"
            }
        ],
    });
}