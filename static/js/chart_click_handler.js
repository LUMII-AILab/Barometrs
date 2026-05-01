function addRequestPredictedCommentsOnClickToChart($divElem) {
    function setLanguageAndRequestDate($divElem, date) {
        const requestForm = $('#analysisRequestForm');
        $('#requestDate').html(date);

        let language = 'all';

        if ($divElem.hasClass('lv-chart')) {
            language = 'lv';
        } else if ($divElem.hasClass('ru-chart')) {
            language = 'ru';
        }

        requestForm.find('[name="requestDate"]').val(date);
        requestForm.find('[name="language"]').val(language);
    }

    function afterDateClick() {
        // createArticlesTable();
        // createClusteredArticlesTable();
        createPrecictedCommentsTable();
        createEmotionKeywordsTable();
        createAggressiveKeywordsTable();
    }

    $divElem[0].on('plotly_click', function (data) {
        console.log('Data point click:', data);
        if (data.points) {
            data.points.forEach(function (pt) {
                const date = pt.x;

                setLanguageAndRequestDate($divElem, date);

                afterDateClick();
            });
        }
    });
}