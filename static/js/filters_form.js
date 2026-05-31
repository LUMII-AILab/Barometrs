$(document).ready(function() {
    const defaultStartMonth = $('#analysisStartMonth').val();
    const defaultEndMonth = $('#analysisEndMonth').val();

    $('#resetAllFilters').on('click', function() {
        $('#analysisStartMonth').val(defaultStartMonth);
        $('#analysisEndMonth').val(defaultEndMonth);
        $('#analysisGroupBy').val('month');
        updateMonthOptions();
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

function updateChartOverlays() {
    updateEmotionChartOverlays();
    updateAggressivenessChartOverlays();
}
