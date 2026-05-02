let _aggressivenessChart = null;
let _aggressivenessData = null;
let _aggressivenessResizeHandler = null;

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
        plotAggressivenessChart(lvResult[0], ruResult[0], 'aggressivenessRatioChart', groupBy);
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

function downloadAggressivenessXls() {
    if (!_aggressivenessData) return;
    const { lvData, ruData, combinedY, lvY, ruY, lvSMA, ruSMA, combinedSMA } = _aggressivenessData;

    const ruIdxByDate = Object.fromEntries(ruData.map(function(d, i) { return [d.date, i]; }));

    let html = '<html xmlns:o="urn:schemas-microsoft-com:office:office"'
        + ' xmlns:x="urn:schemas-microsoft-com:office:excel">'
        + '<head><meta charset="utf-8"></head><body><table>';
    html += '<tr><th>Date</th><th>LV (%)</th><th>LV Trend (%)</th>'
        + '<th>RU (%)</th><th>RU Trend (%)</th>'
        + '<th>LV+RU (%)</th><th>LV+RU Trend (%)</th></tr>';

    lvData.forEach(function(d, i) {
        const ruIdx = ruIdxByDate[d.date];
        const ruVal  = ruIdx !== undefined ? ruY[ruIdx]  : '';
        const ruSmaVal = ruIdx !== undefined ? ruSMA[ruIdx] : '';
        html += '<tr>'
            + '<td>' + d.date + '</td>'
            + '<td>' + lvY[i] + '</td>'
            + '<td>' + lvSMA[i] + '</td>'
            + '<td>' + ruVal + '</td>'
            + '<td>' + ruSmaVal + '</td>'
            + '<td>' + combinedY[i] + '</td>'
            + '<td>' + combinedSMA[i] + '</td>'
            + '</tr>';
    });

    html += '</table></body></html>';

    const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'aggressiveness_data.xls';
    a.click();
    URL.revokeObjectURL(url);
}

function updateAggressivenessChartOverlays() {
    if (!_aggressivenessChart || !_aggressivenessData) return;

    const markAreaData = [];
    $('.event-overlay-tag.active').each(function() {
        const tag = $(this);
        const isCovid = tag.hasClass('event-tag-covid');
        markAreaData.push([
            {
                xAxis: tag.data('start') + '-01',
                itemStyle: { color: isCovid ? 'rgba(55,138,221,0.12)' : 'rgba(216,90,48,0.12)' }
            },
            { xAxis: tag.data('end') + '-28' }
        ]);
    });

    _aggressivenessChart.setOption({
        series: _aggressivenessData.series.concat([
            { name: '__overlays__', type: 'line', data: [], markArea: { silent: true, data: markAreaData } }
        ])
    }, { replaceMerge: ['series'] });
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

    const win = smaWindow(groupBy);
    const lvY = lvData.map(d => d.weighted_aggressiveness_ratio * 100);
    const ruY = ruData.map(d => d.weighted_aggressiveness_ratio * 100);
    const lvSMA = computeSMA(lvY, win);
    const ruSMA = computeSMA(ruY, win);
    const combinedSMA = computeSMA(combinedY, win);

    const dataSeries = [
        {
            name: 'LV',
            type: 'line',
            data: lvData.map((d, i) => [d.date, lvY[i]]),
            itemStyle: { color: '#D62828' },
            lineStyle: { color: '#D62828' }
        },
        {
            name: 'LV trend',
            type: 'line',
            symbol: 'none',
            data: lvData.map((d, i) => [d.date, lvSMA[i]]),
            itemStyle: { color: '#D62828' },
            lineStyle: { color: '#D62828', type: 'dashed', width: 1.5, opacity: 0.7 }
        },
        {
            name: 'RU',
            type: 'line',
            data: ruData.map((d, i) => [d.date, ruY[i]]),
            itemStyle: { color: '#1565C0' },
            lineStyle: { color: '#1565C0' }
        },
        {
            name: 'RU trend',
            type: 'line',
            symbol: 'none',
            data: ruData.map((d, i) => [d.date, ruSMA[i]]),
            itemStyle: { color: '#1565C0' },
            lineStyle: { color: '#1565C0', type: 'dashed', width: 1.5, opacity: 0.7 }
        },
        {
            name: 'LV+RU',
            type: 'line',
            data: combinedX.map((d, i) => [d, combinedY[i]]),
            itemStyle: { color: '#6A0DAD' },
            lineStyle: { color: '#6A0DAD' }
        },
        {
            name: 'LV+RU trend',
            type: 'line',
            symbol: 'none',
            data: combinedX.map((d, i) => [d, combinedSMA[i]]),
            itemStyle: { color: '#6A0DAD' },
            lineStyle: { color: '#6A0DAD', type: 'dashed', width: 1.5, opacity: 0.7 }
        }
    ];

    _aggressivenessData = { lvData, ruData, combinedX, combinedY, lvY, ruY, lvSMA, ruSMA, combinedSMA, series: dataSeries };

    const dom = document.getElementById(chartId);
    if (_aggressivenessChart) _aggressivenessChart.dispose();
    _aggressivenessChart = echarts.init(dom, null, { height: 500 });

    _aggressivenessChart.setOption({
        title: { text: getQuantifier(groupBy) + ' Aggressiveness Ratio' },
        tooltip: {
            trigger: 'axis',
            valueFormatter: function(value) {
                return value !== null && value !== undefined ? value.toFixed(4) + '%' : '-';
            }
        },
        legend: {
            bottom: '55px',
            data: ['LV', 'LV trend', 'RU', 'RU trend', 'LV+RU', 'LV+RU trend']
        },
        grid: {
            bottom: '120px'
        },
        dataZoom: [
            { type: 'inside', xAxisIndex: 0 },
            { type: 'slider', xAxisIndex: 0, bottom: '10px', height: '40px' }
        ],
        toolbox: {
            feature: {
                dataZoom: { yAxisIndex: 'none', title: { zoom: 'Zoom', back: 'Reset zoom' } },
                saveAsImage: { title: 'Download PNG' },
                myXls: {
                    show: true,
                    title: 'Download XLS',
                    icon: 'path://M12,16L7,11H10V4H14V11H17L12,16ZM5,18H19V20H5V18Z',
                    onclick: downloadAggressivenessXls
                }
            }
        },
        xAxis: { type: 'time' },
        yAxis: {
            type: 'value',
            name: 'Aggressiveness (%)',
            axisLabel: { formatter: function(v) { return v.toFixed(4); } }
        },
        series: dataSeries.concat([
            { name: '__overlays__', type: 'line', data: [], markArea: { silent: true, data: [] } }
        ])
    });

    if (_aggressivenessResizeHandler) window.removeEventListener('resize', _aggressivenessResizeHandler);
    _aggressivenessResizeHandler = function() { _aggressivenessChart.resize(); };
    window.addEventListener('resize', _aggressivenessResizeHandler);

    addRequestPredictedCommentsOnClickToAggressivenessChart(_aggressivenessChart);
}