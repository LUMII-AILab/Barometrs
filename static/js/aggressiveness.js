function fetchAndPlotAggressiveness(formData, groupBy) {
    const startDate = formData.startMonth + '-01';
    const d = new Date(formData.endMonth + '-01');
    d.setMonth(d.getMonth() + 1);
    d.setDate(0);
    const endDate = d.toISOString().slice(0, 10);

    $.when(
        $.getJSON('/aggressiveness_by_period', { language: 'lv', startDate: startDate, endDate: endDate, groupBy: groupBy }),
        $.getJSON('/aggressiveness_by_period', { language: 'ru', startDate: startDate, endDate: endDate, groupBy: groupBy })
    ).done(function(lvResult, ruResult) {
        const lvData = lvResult[0];
        const ruData = ruResult[0];
        plotAggressivenessChart(lvData, 'aggressivenessRatioChartLV', groupBy, 'LV');
        plotAggressivenessChart(ruData, 'aggressivenessRatioChartRU', groupBy, 'RU');
        plotAggressivenessCombinedChart(lvData, ruData, 'aggressivenessRatioChartTotal', groupBy, 'LV+RU');
        $('#aggressivenessCharts').height('auto');
    }).fail(function(error) {
        console.error('Error fetching aggressiveness data:', error);
        $('#aggressivenessCharts').height('auto');
    });
}

function renderAggressivenessChart(chartId, x, y, groupBy, language) {
    Plotly.newPlot(chartId, [{
        x: x,
        y: y,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Aggressiveness Ratio',
        line: { color: '#D62828' }
    }], {
        title: getQuantifier(groupBy) + ' Aggressiveness Ratio (' + language + ')',
        xaxis: getXAxisConfig(x[0], groupBy),
        yaxis: { title: 'Aggressiveness (%)', tickformat: '.4f' }
    }, { responsive: true });
}

function plotAggressivenessChart(data, chartId, groupBy, language) {
    renderAggressivenessChart(
        chartId,
        data.map(d => d.date),
        data.map(d => d.weighted_aggressiveness_ratio * 100),
        groupBy,
        language
    );
}

function plotAggressivenessCombinedChart(lvData, ruData, chartId, groupBy, language) {
    const ruByDate = Object.fromEntries(ruData.map(d => [d.date, d]));

    const x = [];
    const y = [];
    lvData.forEach(function(lv) {
        const ru = ruByDate[lv.date];
        const totalWeightSum = lv.aggressive_word_weight_sum + (ru ? ru.aggressive_word_weight_sum : 0);
        const totalWords = lv.total_word_count + (ru ? ru.total_word_count : 0);
        x.push(lv.date);
        y.push(totalWords > 0 ? totalWeightSum / totalWords * 100 : 0);
    });

    renderAggressivenessChart(chartId, x, y, groupBy, language);
}