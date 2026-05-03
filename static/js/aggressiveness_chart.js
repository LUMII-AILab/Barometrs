let _aggressivenessChart = null;
let _aggressivenessData = null;
let _aggressivenessResizeHandler = null;

function _buildDateRange(formData) {
    const startDate = formData.startMonth + '-01';
    const d = new Date(formData.endMonth + '-01');
    d.setMonth(d.getMonth() + 1);
    d.setDate(0);
    return { startDate, endDate: d.toISOString().slice(0, 10) };
}

function fetchAndPlotAggressiveness(formData, groupBy) {
    const { startDate, endDate } = _buildDateRange(formData);

    $.when(
        $.getJSON('/aggressiveness_by_period', { language: 'lv', startDate, endDate, groupBy }),
        $.getJSON('/aggressiveness_by_period', { language: 'ru', startDate, endDate, groupBy })
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
    const { lvData, ruData, lvY, ruY, lvSMA, ruSMA, lvWeightedSMA, ruWeightedSMA } = _aggressivenessData;

    const ruIdxByDate = Object.fromEntries(ruData.map(function(d, i) { return [d.date, i]; }));

    let html = '<html xmlns:o="urn:schemas-microsoft-com:office:office"'
        + ' xmlns:x="urn:schemas-microsoft-com:office:excel">'
        + '<head><meta charset="utf-8"></head><body><table>';
    html += '<tr><th>Date</th>'
        + '<th>LV (%)</th><th>LV Trend (%)</th><th>LV Weighted Trend (%)</th>'
        + '<th>RU (%)</th><th>RU Trend (%)</th><th>RU Weighted Trend (%)</th></tr>';

    lvData.forEach(function(d, i) {
        const ruIdx = ruIdxByDate[d.date];
        const ruVal = ruIdx !== undefined ? ruY[ruIdx] : '';
        const ruSmaVal = ruIdx !== undefined ? ruSMA[ruIdx] : '';
        const ruWeightedSmaVal = ruIdx !== undefined ? ruWeightedSMA[ruIdx] : '';
        html += '<tr>'
            + '<td>' + d.date + '</td>'
            + '<td>' + lvY[i] + '</td>'
            + '<td>' + lvSMA[i] + '</td>'
            + '<td>' + lvWeightedSMA[i] + '</td>'
            + '<td>' + ruVal + '</td>'
            + '<td>' + ruSmaVal + '</td>'
            + '<td>' + ruWeightedSmaVal + '</td>'
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
    const win = smaWindow(groupBy);

    const lvY = lvData.map(d => d.unweighted_aggressiveness_ratio);
    const ruY = ruData.map(d => d.unweighted_aggressiveness_ratio);
    const lvSMA = computeSMA(lvY, win);
    const ruSMA = computeSMA(ruY, win);
    const lvWeightedSMA = computeSMA(lvData.map(d => d.weighted_aggressiveness_ratio), win);
    const ruWeightedSMA = computeSMA(ruData.map(d => d.weighted_aggressiveness_ratio), win);

const series = [
        {
            name: 'LV actual',
            type: 'line',
            symbol: 'circle',
            symbolSize: 4,
            data: lvData.map((d, i) => [d.date, lvY[i]]),
            itemStyle: { color: '#D62828', opacity: 0.5 },
            lineStyle: { color: '#D62828', width: 1, opacity: 0.4 }
        },
        {
            name: 'LV trend',
            type: 'line',
            symbol: 'circle',
            symbolSize: 5,
            showSymbol: false,
            data: lvData.map((d, i) => [d.date, lvSMA[i]]),
            itemStyle: { color: '#D62828' },
            lineStyle: { color: '#D62828', type: 'dashed', width: 2.5, opacity: 0.85 }
        },
        {
            name: 'LV weighted trend',
            type: 'line',
            symbol: 'diamond',
            symbolSize: 6,
            showSymbol: false,
            data: lvData.map((d, i) => [d.date, lvWeightedSMA[i]]),
            itemStyle: { color: '#E85D04' },
            lineStyle: { color: '#E85D04', type: [8, 4], width: 2.5, opacity: 0.85 }
        },
        {
            name: 'RU actual',
            type: 'line',
            symbol: 'circle',
            symbolSize: 4,
            data: ruData.map((d, i) => [d.date, ruY[i]]),
            itemStyle: { color: '#1565C0', opacity: 0.5 },
            lineStyle: { color: '#1565C0', width: 1, opacity: 0.4 }
        },
        {
            name: 'RU trend',
            type: 'line',
            symbol: 'circle',
            symbolSize: 5,
            showSymbol: false,
            data: ruData.map((d, i) => [d.date, ruSMA[i]]),
            itemStyle: { color: '#1565C0', type: 'dashed', width: 2.5, opacity: 0.85 },
            lineStyle: { color: '#1565C0', type: 'dashed', width: 2.5, opacity: 0.85 }
        },
        {
            name: 'RU weighted trend',
            type: 'line',
            symbol: 'diamond',
            symbolSize: 6,
            showSymbol: false,
            data: ruData.map((d, i) => [d.date, ruWeightedSMA[i]]),
            itemStyle: { color: '#0288D1' },
            lineStyle: { color: '#0288D1', type: [8, 4], width: 2.5, opacity: 0.85 }
        }
    ];

    _aggressivenessData = { lvData, ruData, lvY, ruY, lvSMA, ruSMA, lvWeightedSMA, ruWeightedSMA, series };

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
            data: ['LV actual', 'LV trend', 'LV weighted trend', 'RU actual', 'RU trend', 'RU weighted trend']
        },
        grid: { bottom: '120px' },
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
        series: series.concat([
            { name: '__overlays__', type: 'line', data: [], markArea: { silent: true, data: [] } }
        ])
    });

    if (_aggressivenessResizeHandler) window.removeEventListener('resize', _aggressivenessResizeHandler);
    _aggressivenessResizeHandler = function() { _aggressivenessChart.resize(); };
    window.addEventListener('resize', _aggressivenessResizeHandler);

    addRequestPredictedCommentsOnClickToAggressivenessChart(_aggressivenessChart);
}
