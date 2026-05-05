let _aggressivenessWebsiteChart = null;
let _aggressivenessWebsiteResizeHandler = null;

const _WEBSITE_COLORS = {
    lv: { tvnet: '#D62828', apollo: '#E85D04', delfi: '#F9A03F' },
    ru: { tvnet: '#1565C0', apollo: '#0288D1', delfi: '#00ACC1' }
};

const _WEBSITE_LABELS = {
    tvnet: 'TVNET',
    apollo: 'Apollo',
    delfi: 'Delfi',
}

function fetchAndPlotAggressivenessByWebsite(formData, groupBy) {
    const { startDate, endDate } = _buildDateRange(formData);

    $.getJSON('/aggressiveness_by_period_per_website', { startDate, endDate, groupBy })
        .done(function(result) {
            plotAggressivenessByWebsiteChart(result, 'aggressivenessWebsiteChart', groupBy);
            $('#aggressivenessCharts').height('auto');
        })
        .fail(function(error) {
            console.error('Error fetching aggressiveness data by website:', error);
            $('#aggressivenessCharts').height('auto');
        });
}

function plotAggressivenessByWebsiteChart(result, chartId, groupBy) {
    const win = smaWindow(groupBy);
    const series = [];
    const legendData = [];

    ['lv', 'ru'].forEach(function(lang) {
        ['tvnet', 'apollo', 'delfi'].forEach(function(website) {
            const data = (result[lang] && result[lang][website]) || [];
            const y = data.map(d => d.unweighted_aggressiveness_ratio);
            const sma = computeSMA(y, win);
            const color = _WEBSITE_COLORS[lang][website];
            const label = lang.toUpperCase() + ' ' + _WEBSITE_LABELS[website];

            legendData.push(label + ' actual', label + ' trend');

            series.push({
                name: label + ' actual',
                type: 'line',
                symbol: 'circle',
                symbolSize: 4,
                data: data.map((d, i) => [d.date, y[i]]),
                itemStyle: { color, opacity: 0.5 },
                lineStyle: { color, width: 1, opacity: 0.4 }
            });
            series.push({
                name: label + ' trend',
                type: 'line',
                showSymbol: false,
                smooth: 0.3,
                data: data.map((d, i) => [d.date, sma[i]]),
                itemStyle: { color },
                lineStyle: { color, type: 'dashed', width: 2.5, opacity: 0.85 }
            });
        });
    });

    const dom = document.getElementById(chartId);
    if (_aggressivenessWebsiteChart) _aggressivenessWebsiteChart.dispose();
    _aggressivenessWebsiteChart = echarts.init(dom, null, { height: 500 });

    _aggressivenessWebsiteChart.setOption({
        title: { text: getQuantifier(groupBy) + ' Aggressiveness Ratio by Website' },
        tooltip: {
            trigger: 'axis',
            valueFormatter: function(value) {
                return value !== null && value !== undefined ? value.toFixed(4) + '%' : '-';
            }
        },
        legend: { bottom: '55px', data: legendData },
        grid: { bottom: '120px' },
        dataZoom: [
            { type: 'inside', xAxisIndex: 0 },
            { type: 'slider', xAxisIndex: 0, bottom: '10px', height: '40px' }
        ],
        toolbox: { feature: { saveAsImage: { title: 'Download PNG' } } },
        xAxis: { type: 'time' },
        yAxis: {
            type: 'value',
            name: 'Aggressiveness (%)',
            axisLabel: { formatter: function(v) { return v.toFixed(4); } }
        },
        series
    });

    if (_aggressivenessWebsiteResizeHandler) window.removeEventListener('resize', _aggressivenessWebsiteResizeHandler);
    _aggressivenessWebsiteResizeHandler = function() { _aggressivenessWebsiteChart.resize(); };
    window.addEventListener('resize', _aggressivenessWebsiteResizeHandler);
}
