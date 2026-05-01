$(document).ready(function() {
    const defaultStartMonth = $('#analysisStartMonth').val();
    const defaultEndMonth = $('#analysisEndMonth').val();

    $('#resetAllFilters').on('click', function() {
        $('#analysisStartMonth').val(defaultStartMonth);
        $('#analysisEndMonth').val(defaultEndMonth);
        $('#analysisGroupBy').val('month');
        $('#chartOption').val('lv');
        $('#compactLayoutCheckbox').prop('checked', true);
        updateMonthOptions();
        updateCharts('lv');
    });
});

function updateMonthOptions() {
    const startMonth = $('#analysisStartMonth');
    const endMonth = $('#analysisEndMonth');
    const startMonthValue = startMonth.find(':selected').val();
    const endMonthValue = endMonth.find(':selected').val();
    if (startMonthValue) {
        endMonth.find('option').each(function() {
            $(this).prop('disabled', this.value < startMonthValue);
        });
    }
    if (endMonthValue) {
        startMonth.find('option').each(function() {
            $(this).prop('disabled', this.value > endMonthValue);
        });
    }
}
updateMonthOptions();

$('.event-overlay-tag').on('click', function() {
    $(this).toggleClass('active');
    updateChartOverlays();
});

function getOverlayShapes() {
    const shapes = [];
    $('.event-overlay-tag.active').each(function() {
        const tag = $(this);
        const isCovid = tag.hasClass('event-tag-covid');
        shapes.push({
            type: 'rect',
            xref: 'x',
            yref: 'paper',
            x0: tag.data('start') + '-01',
            x1: tag.data('end') + '-28',
            y0: 0,
            y1: 1,
            fillcolor: isCovid ? 'rgba(55,138,221,0.12)' : 'rgba(216,90,48,0.12)',
            opacity: 1,
            line: { width: 0 },
            layer: 'below'
        });
    });
    return shapes;
}

function updateChartOverlays() {
    const timeSeriesChartIds = [
        'emotionsPercentDayChartLV', 'emotionsPercentDayChartRU', 'emotionsPercentDayChartTotal',
        'emotionsCountDayChartLV', 'emotionsCountDayChartRU', 'emotionsCountDayChartTotal',
        'commentAndArticleCountChartLV', 'commentAndArticleCountChartRU', 'commentAndArticleCountChartTotal',
        'aggressivenessRatioChartLV', 'aggressivenessRatioChartRU', 'aggressivenessRatioChartTotal'
    ];
    const shapes = getOverlayShapes();
    timeSeriesChartIds.forEach(function(chartId) {
        const el = document.getElementById(chartId);
        if (el && el._fullLayout) {
            Plotly.relayout(chartId, { shapes: shapes });
        }
    });
}
