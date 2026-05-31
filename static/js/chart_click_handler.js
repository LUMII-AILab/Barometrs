function addRequestPredictedCommentsOnClickToAggressivenessChart(chart) {
    const $requestForm = $('#analysisRequestForm');

    chart.on('click', function(params) {
        if (!Array.isArray(params.value)) return;
        const name = params.seriesName || '';
        const language = name.startsWith('LV') ? 'lv' : name.startsWith('RU') ? 'ru' : 'all';
        const d = new Date(params.value[0]);
        const date = d.getUTCFullYear() + '-' +
            String(d.getUTCMonth() + 1).padStart(2, '0') + '-' +
            String(d.getUTCDate()).padStart(2, '0');
        $('#requestDate').html(date);
        $requestForm.find('[name="requestDate"]').val(date);
        $requestForm.find('[name="language"]').val(language);
        createPredictedCommentsTable();
        createAggressiveKeywordsTable();
    });
}

