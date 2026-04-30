function createPrecictedCommentsTable() {
    var table = new Tabulator("#predictedCommentsTable", {
        ajaxURL: "/predicted_comments_emotion_comments",
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
            return data.article_title + 'separator' + data.article_id + 'separator' + data.article_url;
        },
        groupHeader: function(value, count, data, group){
            if (value === 'undefined') {
                setGroupBy(false);
                return;
            }

            // If value contains 'emotion', then it is a group by emotion
            if (value.includes('emotion_separator')) {
                emotion = value.split('emotion_separator')[0];
                return "Emotion: " + emotion + "<span style='color:#d00; margin-left:10px;'>(" + count + " comments)</span>";
            } else {
                article_title = value.split('separator')[0];
                article_url = value.split('separator')[2];
                article_url_element = "<a href='" + article_url + "' target='_blank'>" + article_url + "</a>";

                return article_title + ' ' + article_url_element + "<span style='color:#d00; margin-left:10px;'>(" + count + " comments)</span>";
            }
        },
        columns: [
            {title: "ID", field: "id", width: 30},
            {title: "Comment", field: "comment_text", formatter: "textarea", hozAlign: "left", headerFilter: "input"},
            {title: "Language", field: "comment_lang", hozAlign: "left", width: 30},
            {title: "Article ID", field: "article_id", hozAlign: "left", width: 30, visible: false},
            {title: "Article Title", field: "article_title", hozAlign: "left", width: 30, visible: false},
            {title: "Article URL", field: "article_url", hozAlign: "left", width: 30, visible: false},
            {title: "Emotion", field: "prediction", hozAlign: "left", width: 100, headerFilter: "input"},
            {title: "Score", field: "prediction_score", formatter: cell => cell.getValue() + "%", hozAlign: "left", width: 100},
        ],
    });

    // Get group toggle button
    const groupToggle = $('#groupCommentsBy');

    // clear previous click events
    groupToggle.off('click');

    // reset button value and text
    groupToggle.val('emotions');
    groupToggle.text('Group by: Articles');

    groupToggle.on('click', function() {
        const value = groupToggle.val();
        if (value === 'emotions') {
            table.setGroupBy(function(data) {
                return data.prediction + 'emotion_separator';
            });
            new_value = 'articles'
            new_text = 'Group by: Emotions'
        } else {
            table.setGroupBy(function(data) {
                return data.article_title + 'separator' + data.article_id + 'separator' + data.article_url;
            });
            new_value = 'emotions'
            new_text = 'Group by: Articles'
        }

        // Set group toggle button value
        groupToggle.val(new_value);
        groupToggle.text(new_text);
    });
}