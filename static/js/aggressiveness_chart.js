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
        plotAggressivenessChart(lvData, ruData, 'aggressivenessRatioChart', groupBy);
        $('#aggressivenessCharts').height('auto');
    }).fail(function(error) {
        console.error('Error fetching aggressiveness data:', error);
        $('#aggressivenessCharts').height('auto');
    });
}

function smaWindow(groupBy) {
    if (groupBy === 'day') return 7;
    if (groupBy === 'week') return 4;
    return 3;
}

function computeSMA(values, window) {
    return values.map(function(_, i) {
        const slice = values.slice(Math.max(0, i - window + 1), i + 1);
        return slice.reduce(function(a, b) { return a + b; }, 0) / slice.length;
    });
}

function plotAggressivenessChart(lvData, ruData, chartId, groupBy) {
    const ruByDate = Object.fromEntries(ruData.map(d => [d.date, d]));

    const combinedX = [];
    const combinedY = [];
    lvData.forEach(function(lv) {
        const ru = ruByDate[lv.date];
        const totalWeightSum = lv.aggressive_word_weight_sum + (ru ? ru.aggressive_word_weight_sum : 0);
        const totalWords = lv.total_word_count + (ru ? ru.total_word_count : 0);
        combinedX.push(lv.date);
        combinedY.push(totalWords > 0 ? totalWeightSum / totalWords * 100 : 0);
    });

    const traces = [
        {
            x: lvData.map(d => d.date),
            y: lvData.map(d => d.weighted_aggressiveness_ratio * 100),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'LV',
            line: { color: '#D62828' }
        },
        {
            x: ruData.map(d => d.date),
            y: ruData.map(d => d.weighted_aggressiveness_ratio * 100),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'RU',
            line: { color: '#1565C0' }
        },
        {
            x: combinedX,
            y: combinedY,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'LV+RU',
            line: { color: '#6A0DAD' }
        }
    ];

    const win = smaWindow(groupBy);
    const lvSMA = computeSMA(lvData.map(d => d.weighted_aggressiveness_ratio * 100), win);
    const ruSMA = computeSMA(ruData.map(d => d.weighted_aggressiveness_ratio * 100), win);
    const combinedSMA = computeSMA(combinedY, win);

    traces.push(
        {
            x: lvData.map(d => d.date),
            y: lvSMA,
            type: 'scatter',
            mode: 'lines',
            name: 'LV trend',
            line: { color: '#D62828', dash: 'dash', width: 1.5 },
            opacity: 0.7
        },
        {
            x: ruData.map(d => d.date),
            y: ruSMA,
            type: 'scatter',
            mode: 'lines',
            name: 'RU trend',
            line: { color: '#1565C0', dash: 'dash', width: 1.5 },
            opacity: 0.7
        },
        {
            x: combinedX,
            y: combinedSMA,
            type: 'scatter',
            mode: 'lines',
            name: 'LV+RU trend',
            line: { color: '#6A0DAD', dash: 'dash', width: 1.5 },
            opacity: 0.7
        }
    );

    const allDates = lvData.map(d => d.date).concat(ruData.map(d => d.date));

    Plotly.newPlot(chartId, traces, {
        title: getQuantifier(groupBy) + ' Aggressiveness Ratio',
        xaxis: getXAxisConfig(allDates[0], groupBy),
        yaxis: { title: 'Aggressiveness (%)', tickformat: '.4f' }
    }, { responsive: true });

    addRequestPredictedCommentsOnClickToAggressivenessChart($('#' + chartId));
}