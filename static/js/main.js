function getQuantifier(groupBy) {
    if (groupBy === 'month') return 'Monthly';
    if (groupBy === 'week') return 'Weekly';
    if (groupBy === 'day') return 'Daily';
    return '';
}

// ECharts instances and base series data for emotion charts, keyed by container ID
const emotionCharts = {};
const _emotionChartSeries = {};

function updateEmotionChartOverlays() {
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
    const overlaysSeries = { name: '__overlays__', type: 'line', data: [], markArea: { silent: true, data: markAreaData } };
    Object.entries(emotionCharts).forEach(function([chartId, chart]) {
        const base = _emotionChartSeries[chartId] || [];
        chart.setOption({ series: base.concat([overlaysSeries]) }, { replaceMerge: ['series'] });
    });
}

function handleEmotionChartClick(date, lang) {
    const requestForm = $('#analysisRequestForm');
    $('#requestDate').html(date);
    requestForm.find('[name="requestDate"]').val(date);
    requestForm.find('[name="language"]').val(lang);
    createPredictedCommentsTable();
    createEmotionKeywordsTable();
    createAggressiveKeywordsTable();
}

$(document).ready(function() {
    const colorMap = {
        "neutral":  "#D9D9D9",
        "joy":      "#FFC72C",
        "surprise": "#FF8C42",
        "anger":    "#D62828",
        "sadness":  "#2878B5",
        "fear":     "#7A3EB1",
        "disgust":  "#6DAA2C"
    };

    const EMOTIONS = Object.keys(colorMap);

    window.addEventListener('resize', function() {
        Object.values(emotionCharts).forEach(c => c.resize());
    });

    $('#requestAnalysis').click(function () {
        Object.values(emotionCharts).forEach(c => c.dispose());
        Object.keys(emotionCharts).forEach(k => delete emotionCharts[k]);
        Object.keys(_emotionChartSeries).forEach(k => delete _emotionChartSeries[k]);

        $('.loading-spinners').show();
        $('#charts').hide();
        $('#aggressivenessCharts').height('0');

        const requestForm = $('#analysisRequestForm');
        requestForm.find('[name="currentPredictionType"]').val(requestForm.find('[name="predictionType"]').val());
        requestAndProcessAnalysisData();
    });

    function requestAndProcessAnalysisData() {
        const form = $('#analysisRequestForm');
        const groupBy = form.find('[name="analysisGroupBy"]').val();
        const formData = {
            startMonth: form.find('[name="analysisStartMonth"]').val(),
            endMonth: form.find('[name="analysisEndMonth"]').val(),
            groupBy: form.find('[name="analysisGroupBy"]').val(),
            predictionType: form.find('[name="currentPredictionType"]').val()
        };

        $.ajax({
            url: '/predicted_comments_max_emotion_charts',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            dataType: 'json',
            success: function (data) {
                plotEmotionsPercentPeriodChart(data.lv, data.ru, 'emotionsPercentDayChart', groupBy);
                plotCommentAndArticleCountChart(data.lv, data.ru, 'commentAndArticleCountChart', groupBy);
            },
            error: function (error) {
                console.error('There was an error!', error);
            },
            complete: function() {
                $('.loading-spinners').hide();
                $('#charts').show();
                Object.values(emotionCharts).forEach(c => c.resize());
                setTimeout(updateChartOverlays, 500);
            }
        });

        fetchAndPlotAggressiveness(formData, groupBy);
        fetchAndPlotAggressivenessByWebsite(formData, groupBy);
    }

    function initChart(chartId) {
        const dom = document.getElementById(chartId);
        if (emotionCharts[chartId]) emotionCharts[chartId].dispose();
        const chart = echarts.init(dom);
        emotionCharts[chartId] = chart;
        return chart;
    }

    function extractDate(params) {
        const d = new Date(params.value[0]);
        return d.getUTCFullYear() + '-' +
            String(d.getUTCMonth() + 1).padStart(2, '0') + '-' +
            String(d.getUTCDate()).padStart(2, '0');
    }

    function registerClickHandler(chart) {
        chart.on('click', function(params) {
            if (!Array.isArray(params.value)) return;
            const lang = params.seriesName.startsWith('LV') ? 'lv'
                       : params.seriesName.startsWith('RU') ? 'ru' : 'all';
            handleEmotionChartClick(extractDate(params), lang);
        });
    }

    function mergedLineSeries(lvData, ruData, emotion) {
        const color = colorMap[emotion] || '#888';
        return [
            {
                name: 'LV ' + emotion,
                type: 'line',
                showSymbol: false,
                data: Object.entries(lvData).map(([p, v]) => [p, v[emotion] || 0]),
                itemStyle: { color },
                lineStyle: { color, type: 'solid' },
                legendGroupId: 'lv'
            },
            {
                name: 'RU ' + emotion,
                type: 'line',
                showSymbol: false,
                data: Object.entries(ruData).map(([p, v]) => [p, v[emotion] || 0]),
                itemStyle: { color },
                lineStyle: { color, type: 'dashed' },
                legendGroupId: 'ru'
            }
        ];
    }

    function dualLegend(lvNames, ruNames) {
        return [
            {
                id: 'lv',
                data: lvNames,
                orient: 'horizontal',
                bottom: '95px',
                left: 'center',
                selector: [{ type: 'all', title: 'All LV' }, { type: 'inverse', title: 'None' }],
                selectorPosition: 'start',
                textStyle: { fontSize: 12 }
            },
            {
                id: 'ru',
                data: ruNames,
                orient: 'horizontal',
                bottom: '55px',
                left: 'center',
                selector: [{ type: 'all', title: 'All RU' }, { type: 'inverse', title: 'None' }],
                selectorPosition: 'start',
                textStyle: { fontSize: 12 }
            }
        ];
    }

    function lineChartBase() {
        return {
            grid: { bottom: '150px' },
            dataZoom: [
                { type: 'inside', xAxisIndex: 0 },
                { type: 'slider', xAxisIndex: 0, bottom: '10px', height: '40px' }
            ],
            toolbox: {
                feature: {
                    dataZoom: { yAxisIndex: 'none', title: { zoom: 'Zoom', back: 'Reset zoom' } },
                    saveAsImage: { title: 'Download PNG' }
                }
            },
            xAxis: { type: 'time' }
        };
    }

    function plotEmotionsPercentPeriodChart(lvData, ruData, chartId, groupBy) {
        const lv = lvData.emotion_percent_per_period;
        const ru = ruData.emotion_percent_per_period;

        const allEmotions = new Set();
        [lv, ru].forEach(d => Object.values(d).forEach(e => Object.keys(e).forEach(em => allEmotions.add(em))));

        const emotions = EMOTIONS.filter(e => allEmotions.has(e));
        const series = emotions.flatMap(e => mergedLineSeries(lv, ru, e));
        _emotionChartSeries[chartId] = series;

        const chart = initChart(chartId);
        chart.setOption({
            ...lineChartBase(),
            title: { text: getQuantifier(groupBy) + ' % of Predominant Emotions — LV (solid) vs RU (dashed)' },
            tooltip: {
                trigger: 'axis',
                valueFormatter: v => v != null ? (v * 100).toFixed(2) + '%' : '-'
            },
            legend: dualLegend(emotions.map(e => 'LV ' + e), emotions.map(e => 'RU ' + e)),
            yAxis: {
                type: 'value',
                axisLabel: { formatter: v => (v * 100).toFixed(0) + '%' }
            },
            series
        });
        registerClickHandler(chart);
    }

    function plotCommentAndArticleCountChart(lvData, ruData, chartId, groupBy) {
        const series = [
            { name: 'LV Comments', type: 'line', showSymbol: false,
              data: Object.entries(lvData.comment_count_per_period).map(([d, v]) => [d, v]),
              itemStyle: { color: '#2878B5' }, lineStyle: { color: '#2878B5', type: 'solid' } },
            { name: 'RU Comments', type: 'line', showSymbol: false,
              data: Object.entries(ruData.comment_count_per_period).map(([d, v]) => [d, v]),
              itemStyle: { color: '#2878B5' }, lineStyle: { color: '#2878B5', type: 'dashed' } },
            { name: 'LV Articles', type: 'line', showSymbol: false,
              data: Object.entries(lvData.article_count_per_period).map(([d, v]) => [d, v]),
              itemStyle: { color: '#FF8C42' }, lineStyle: { color: '#FF8C42', type: 'solid' } },
            { name: 'RU Articles', type: 'line', showSymbol: false,
              data: Object.entries(ruData.article_count_per_period).map(([d, v]) => [d, v]),
              itemStyle: { color: '#FF8C42' }, lineStyle: { color: '#FF8C42', type: 'dashed' } }
        ];
        _emotionChartSeries[chartId] = series;

        const chart = initChart(chartId);
        chart.setOption({
            ...lineChartBase(),
            title: { text: getQuantifier(groupBy) + ' Comment and Article Count — LV (solid) vs RU (dashed)' },
            tooltip: { trigger: 'axis' },
            legend: [
                {
                    data: ['LV Comments', 'LV Articles'],
                    orient: 'horizontal', bottom: '95px', left: 'center',
                    selector: [{ type: 'all', title: 'All LV' }, { type: 'inverse', title: 'None' }],
                    selectorPosition: 'start'
                },
                {
                    data: ['RU Comments', 'RU Articles'],
                    orient: 'horizontal', bottom: '55px', left: 'center',
                    selector: [{ type: 'all', title: 'All RU' }, { type: 'inverse', title: 'None' }],
                    selectorPosition: 'start'
                }
            ],
            yAxis: { type: 'value', name: 'Count' },
            series
        });
        registerClickHandler(chart);
    }

    const requestForm = $('#analysisRequestForm');
    requestForm.find('[name="currentPredictionType"]').val(requestForm.find('[name="predictionType"]').val());
    requestAndProcessAnalysisData();
});


const tabVisibility = {
    '#emotionsTabPane': {
        '.tab-bar-row': true,
        '.controls-card': true,
        '.view-controls': false,
        '.details-header': true,
        '#detailSection': true,
        '#emotionKeywordContainer': true,
        '#aggressiveKeywordContainer': false
    },
    '#aggressivenessTabPane': {
        '.tab-bar-row': true,
        '.controls-card': true,
        '.view-controls': false,
        '.details-header': true,
        '#detailSection': true,
        '#emotionKeywordContainer': false,
        '#aggressiveKeywordContainer': true
    },
    '#kwfreqTabPane': {
        '.tab-bar-row': false,
        '.controls-card': true,
        '.view-controls': false,
        '.details-header': false,
        '#detailSection': false,
        '#emotionKeywordContainer': false,
        '#aggressiveKeywordContainer': false
    },
    '#aggressiveKeywordsListTabPane': {
        '.tab-bar-row': false,
        '.controls-card': false,
        '.view-controls': false,
        '.details-header': false,
        '#detailSection': false,
        '#emotionKeywordContainer': false,
        '#aggressiveKeywordContainer': false
    },
};

document.getElementById('mainTabs').addEventListener('shown.bs.tab', function(e) {
    const config = tabVisibility[e.target.getAttribute('data-bs-target')] ?? {};
    Object.entries(config).forEach(([selector, visible]) => $(selector).toggle(visible));
    window.dispatchEvent(new Event('resize'));
});
