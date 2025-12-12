// Plot charts
$(document).ready(function() {
    const colorMap = {
      "neutral":  "#D9D9D9",  // Softer gray; enough contrast with labels but less glare
      "joy":      "#FFC72C",  // Rich golden yellow; higher contrast vs white backgrounds
      "surprise": "#FF8C42",  // Vivid orange distinct from joy’s yellow
      "anger":    "#D62828",  // Strong red with slightly darker value for text contrast
      "sadness":  "#2878B5",  // Mid-blue with good readability in thin wedges
      "fear":     "#7A3EB1",  // Clear violet; differentiated from both blue and red
      "disgust":  "#6DAA2C"   // Cooler green to separate from yellow/orange family
    }

    $('#requestAnalysis').click(function () {
        // clear previous selection border
        $('.date-range-btn').css('border-width', '2px');

        const requestForm = $('#analysisRequestForm');
        requestForm.find('[name="currentPredictionType"]').val(requestForm.find('[name="predictionType"]').val());
        requestAndProcessAnalysisData();

        $('.chart').each(function() {
            Plotly.purge(this);
        });
    });

    function requestAndProcessAnalysisData() {
        // Get data from form inputs
        const form = $('#analysisRequestForm');
        const groupBy = form.find('[name="analysisGroupBy"]').val();
        const formData = {
            startMonth: form.find('[name="analysisStartMonth"]').val(),
            endMonth: form.find('[name="analysisEndMonth"]').val(),
            groupBy: form.find('[name="analysisGroupBy"]').val(),
            predictionType: form.find('[name="currentPredictionType"]').val()
        };

        // Post request
        $.ajax({
            url: '/predicted_comments_max_emotion_charts',
            type: 'POST',
            contentType: 'application/json', // Set content type to JSON
            data: JSON.stringify(formData), // Convert formData object to JSON
            dataType: 'json',
            success: function (data) {
                // lv
                plotEmotionsPercentPeriodChart(data.lv, 'emotionsPercentDayChartLV', groupBy, 'LV');
                plotEmotionsGroupedPercentPeriodPieChart(data.lv, 'emotionsPercentPieChartLV', 'LV');
                plotEmotionsCountPediodChart(data.lv, 'emotionsCountDayChartLV', groupBy, 'LV');
                plotCommentAndArticleCountChart(data.lv, 'commentAndArticleCountChartLV', groupBy, 'LV');

                // ru
                plotEmotionsPercentPeriodChart(data.ru, 'emotionsPercentDayChartRU', groupBy, 'RU');
                plotEmotionsGroupedPercentPeriodPieChart(data.ru, 'emotionsPercentPieChartRU', 'RU');
                plotEmotionsCountPediodChart(data.ru, 'emotionsCountDayChartRU', groupBy, 'RU');
                plotCommentAndArticleCountChart(data.ru, 'commentAndArticleCountChartRU', groupBy, 'RU');

                // total
                plotEmotionsPercentPeriodChart(data.total, 'emotionsPercentDayChartTotal', groupBy, 'LV+RU');
                plotEmotionsGroupedPercentPeriodPieChart(data.total, 'emotionsPercentPieChartTotal', 'LV+RU');
                plotEmotionsCountPediodChart(data.total, 'emotionsCountDayChartTotal', groupBy, 'LV+RU');
                plotCommentAndArticleCountChart(data.total, 'commentAndArticleCountChartTotal', groupBy, 'LV+RU');
            },
            error: function (error) {
                console.error('There was an error!', error);
            }
        });
    }

    function plotEmotionsPercentPeriodChart(data, chartId, groupBy, language) {
        const chartData = data.emotion_percent_per_period;
        const traces = getEmotionTraces(chartData);

        const layout = {
            title: getQuantifier(groupBy) + ' Percentage of Predominant Emotions in Comments (' + language + ')',
            xaxis: getXAxisConfig(data.chartStart, groupBy),
            yaxis: {
                title: 'Percentage of Emotions (%)',
                tickformat: '.2%',
            }
        };

        Plotly.newPlot(chartId, traces, layout, {responsive: true});

        const chartDiv = $('#' + chartId);

        addRequestPredictedCommentsOnClickToChart(chartDiv);
    }

    function getQuantifier(groupBy) {
        let quantifier = '';
        if (groupBy === 'month') {
            quantifier = 'Monthly';
        } else if (groupBy === 'week') {
            quantifier = 'Weekly';
        } else if (groupBy === 'day') {
            quantifier = 'Daily';
        }

        return quantifier;
    }

    // TODO: fix ticks and tick events.
    function getXAxisConfig(start, groupBy) {
        let config = {};
        if (groupBy === 'month') {
            config = {
                title: 'Month',
                showticklabels: true,
                tickangle: 'auto',
                tick0: start,
                dtick: 'M1',
            };
        } else if (groupBy === 'week') {
            config = {
                title: 'Week',
                showticklabels: true,
                tickangle: 'auto',
                tick0: start,
            };
        } else if (groupBy === 'day') {
            config = {
                title: 'Date',
                showticklabels: true,
                tickangle: 'auto',
                tick0: start,
            };
        }

        return config;
    }

    function getEmotionTraces(data) {
        const traces = [];

        // Iterate over all periods to get all emotions
        const allEmotions = {};
        Object.keys(data).forEach(month => {
            const emotions = data[month];
            Object.keys(emotions).forEach(emotion => {
                allEmotions[emotion] = true;
            });
        });

        // Create a trace for each emotion
        Object.keys(allEmotions).forEach(emotion => {
            const x = [];
            const y = [];

            // Collect data for each period
            Object.keys(data).forEach(period => {
                x.push(period);
                y.push(data[period][emotion] || 0); // Use zero if no data exists for this emotion in the month
            });

            // Push a new trace for the current emotion
            traces.push({
                x: x,
                y: y,
                type: 'scatter',  // Line chart
                mode: 'lines+markers',
                name: emotion,
                line: {
                    color: colorMap[emotion] // Use a predefined color for each emotion
                }
            });
        });

        return traces;
    }

    function plotEmotionsCountPediodChart(data, chartId, groupBy, language) {
        const chartData = data.emotion_count_per_period;
        const traces = getEmotionTraces(chartData);

        const layout = {
            title: getQuantifier(groupBy) + ' Count of Predominant Emotions in Comments (' + language + ')',
            xaxis: getXAxisConfig(data.chartStart, groupBy),
            yaxis: {
                title: 'Count of Comments',
            }
        };

        Plotly.newPlot(chartId, traces, layout, {responsive: true});

        const chartDiv = $('#' + chartId);

        // Add click event to chart
        addRequestPredictedCommentsOnClickToChart(chartDiv);
    }

    // Request predicted comments when a chart point is clicked or a date is selected from the x-axis
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

    function createArticlesTable(data) {
        var table = new Tabulator("#articlesTable", {
            ajaxURL: "/predicted_comments_max_emotion_articles",
            ajaxParams: function(){
                const form = $('#analysisRequestForm');

                return {
                    predictionType: form.find('[name="currentPredictionType"]').val(),
                    requestDate: form.find('[name="requestDate"]').val(),
                    language: form.find('[name="language"]').val(),
                }
            },
            height: 300,
            layout: "fitColumns",
            columns: [
                {title: "ID", field: "id", width: 80},
                {title: "Article", field: "article_title", formatter: "textarea", hozAlign: "left"},
            ],
        });
    }

    function createClusteredArticlesTable() {
        $('.clusterFormDescription').show();
        var table = new Tabulator("#clusteredArticlesTable", {
            ajaxURL: "/predicted_comments_max_emotion_clustered_articles",
            ajaxParams: function(){
                const form = $('#analysisRequestForm');
                const clusterForm = $('#clusteredArticlesForm');

                return {
                    predictionType: form.find('[name="currentPredictionType"]').val(),
                    requestDate: form.find('[name="requestDate"]').val(),
                    language: form.find('[name="language"]').val(),
                    minClusterSize: clusterForm.find('[name="minClusterSize"]').val(),
                    minSamples: clusterForm.find('[name="minSamples"]').val(),
                }
            },
            groupBy: ["cluster"],
            groupHeader: [
                // Cluster name is concatenated list of article titles
                function(value, count, data, group){
                    uniqueArticles = [...new Set(data.map(article => article.article_title))];
                    return '<br>' + uniqueArticles.join(',<br>');
                },
            ],
            height: 500,
            renderVerticalBuffer: 1500,
            layout: "fitColumns",
            columns: [
                {title: "ID", field: "id", width: 80},
                {title: "Cluster", field: "cluster", hozAlign: "left", visible:false},
                {title: "Article", field: "article_title", formatter: "textarea", hozAlign: "left"},
                {title: "Comment text", field: "comment_text", formatter: "textarea", hozAlign: "left"},
                {title: "Emotion", field: "emotion", hozAlign: "left", headerFilter: "input"},
                {title: "Score", field: "emotion_score", formatter: cell => cell.getValue() + "%", hozAlign: "left"},
            ],
        });

        table.on('groupClick', function(e, group){
            group.toggle();
        });
    }

    // $('#clusterArticlesButton').click(function() {
    //     createClusteredArticlesTable();
    // });

    function createPrecictedCommentsTable() {
        var table = new Tabulator("#predictedCommentsTable", {
            ajaxURL: "/predicted_comments_emotion_comments",
            ajaxParams: function(){
                const form = $('#analysisRequestForm');

                return {
                    predictionType: form.find('[name="currentPredictionType"]').val(),
                    requestDate: form.find('[name="requestDate"]').val(),
                    language: form.find('[name="language"]').val(),
                }
            },
            height: 450,
            layout: "fitColumns",
            groupBy: function(data){
                return data.article_title + 'separator' + data.article_id; //groups by data and age
            },
            groupHeader: function(value, count, data, group){
                if (value === 'undefined') {
                    setGroupBy(false);
                    return;
                }

                // If value contains 'emotion', then it is a group by emotion
                if (value.includes('emotion_separator')) {
                    emotion = value.split('emotion_separator')[0];
                    return "Emotion: " + emotion + "<span style='color:#d00; margin-left:10px;'>(" + count + " comments)</span>";
                } else {
                    article = value.split('separator');
                    article_url_element = "<a href='https://delfi.lv/a/" + article[1] + "' target='_blank'>(article)</a>";

                    return article[0] + ' ' + article_url_element + "<span style='color:#d00; margin-left:10px;'>(" + count + " comments)</span>";
                }
            },
            columns: [
                {title: "ID", field: "id", width: 20},
                {title: "Comment", field: "comment_text", formatter: "textarea", hozAlign: "left"},
                {title: "Language", field: "comment_lang", hozAlign: "left", width: 30},
                {title: "Article ID", field: "article_id", hozAlign: "left", width: 30, visible: false},
                {title: "Article Title", field: "article_title", hozAlign: "left", width: 30, visible: false},
                {title: "Emotion", field: "prediction", hozAlign: "left", width: 100, headerFilter: "input"},
                {title: "Score", field: "prediction_score", formatter: cell => cell.getValue() + "%", hozAlign: "left", width: 100},
            ],
        });

        // Get group toggle button
        const groupToggle = $('#groupCommentsBy');
        groupToggle.on('click', function() {
            const value = groupToggle.val();
            if (value === 'emotions') {
                table.setGroupBy(function(data) {
                    return data.prediction + 'emotion_separator';
                });
                new_value = 'articles'
                new_text = 'Group by: Emotions'
            } else {
                table.setGroupBy(function(data) {
                    return data.article_title + 'separator' + data.article_id;
                });
                new_value = 'emotions'
                new_text = 'Group by: Articles'
            }

            // Set group toggle button value
            groupToggle.val(new_value);
            groupToggle.text(new_text);
        });
    }

    function createEmotionKeywordsTable() {
        var table = new Tabulator("#emotionKeywordsTable", {
            ajaxURL: "/predicted_comments_emotion_keywords",
            ajaxParams: function(){
                const form = $('#analysisRequestForm');

                return {
                    predictionType: form.find('[name="currentPredictionType"]').val(),
                    requestDate: form.find('[name="requestDate"]').val(),
                    language: form.find('[name="language"]').val(),
                }
            },
            height: 300,
            layout: "fitColumns",
            columns: [
                {title: "Emotion", field: "emotion", hozAlign: "left", width: 150},
                {
                    title: "Keywords (keyword: score %)",
                    field: "keywords",
                    hozAlign: "left",
                    formatter: function(cell, formatterParams, onRendered) {
                        // Extract keyword array
                        const keywords = cell.getValue();
                        // Map each keyword to a formatted string with percentage
                        const formattedKeywords = keywords.map(keyword => {
                            const scoreAsPercent = (keyword[1] * 100).toFixed(2) + '%';
                            return `${keyword[0]}: ${scoreAsPercent}`;
                        }).sort((a, b) => {
                            // Extract numerical values for sorting
                            const scoreA = parseFloat(a.split(': ')[1]);
                            const scoreB = parseFloat(b.split(': ')[1]);
                            return scoreB - scoreA; // Sort in descending order
                        });
                        // Join all formatted keywords into a single string with line breaks
                        return formattedKeywords.join("<br>");
                    }
                },
            ],
        });
    }

    function plotCommentAndArticleCountChart(data, chartId, groupBy, language) {
        const chartStart = data.chart_start;
        const comment_count_per_period = data.comment_count_per_period;
        const article_count_per_period = data.article_count_per_period;
        const xaxisConfig = getXAxisConfig(chartStart, groupBy);

        const traces = [];
        traces.push({
            x: Object.keys(comment_count_per_period),
            y: Object.values(comment_count_per_period),
            type: 'scatter',  // Line chart
            mode: 'lines+markers',
            name: 'Comment Count',
        });

        traces.push({
            x: Object.keys(article_count_per_period),
            y: Object.values(article_count_per_period),
            type: 'scatter',  // Line chart
            mode: 'lines+markers',
            name: 'Article Count'
        });

        const layout = {
            title: getQuantifier(groupBy) + ' Count of Comments and Commented Articles (' + language + ')',
            xaxis: xaxisConfig,
            yaxis: {
                title: 'Count',
            }
        };

        Plotly.newPlot(chartId, traces, layout, {responsive: true});

        const chartDiv = $('#' + chartId);

        addRequestPredictedCommentsOnClickToChart(chartDiv);
    }

    function plotEmotionsGroupedPercentPeriodPieChart(data, chartId, language) {
        data = data.emotions_grouped_percent_per_period;

        const labels = Object.keys(data);
        const values = Object.values(data);

        const traces = [{
            type: 'pie',
            labels: labels,
            values: values,
            textinfo: 'label+percent',
            textposition: 'outside',
            automargin: true,
            marker: {
                colors: labels.map(emotion => colorMap[emotion])
            }
        }];

        const layout = {
            title: 'Percentage of Predominant Emotions in Comments (' + language + ')',
            showlegend: true,
        };

        Plotly.newPlot(chartId, traces, layout, {responsive: true});
    }

    const requestForm = $('#analysisRequestForm');
    requestForm.find('[name="currentPredictionType"]').val(requestForm.find('[name="predictionType"]').val());
    requestAndProcessAnalysisData();
});


function adjustChartLayout(option) {
    const chartContainer = $('#charts');

    chartContainer.removeClass('show-lv-charts');
    chartContainer.removeClass('show-ru-charts');
    chartContainer.removeClass('show-totals-charts');
    switch(option) {
        case 'all':
            break;
        case 'lv':
            chartContainer.addClass('show-lv-charts');
            break;
        case 'ru':
            chartContainer.addClass('show-ru-charts');
            break;
        case 'totals':
            chartContainer.addClass('show-totals-charts');
            break;
    }
    // trigger resize event to adjust chart layout
    window.dispatchEvent(new Event('resize'));
}

function applyCompactMode(option) {
    const layoutConfig = $('#layoutConfig');
    const checkbox = $('#compactLayoutCheckbox');
    const compactMode = checkbox.is(':checked');
    const chartContainer = $('#charts');

    switch(option) {
        case 'all':
            layoutConfig.hide();
            chartContainer.removeClass('compact-layout');
            break;
        default:
            layoutConfig.css('display', 'inline-block');
            if (!compactMode) {
                chartContainer.removeClass('compact-layout');
            } else {
                chartContainer.addClass('compact-layout');
            }
            break;
    }
    window.dispatchEvent(new Event('resize'));
}

function updateCharts(language) {
    applyCompactMode(language);
    adjustChartLayout(language);

    // as safety measure, trigger resize event with a delay
    setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
    }, 500);
}
updateCharts($('#chartOption').val());

function updateMonthOptions() {
    const startMonth = $('#analysisStartMonth');
    const endMonth = $('#analysisEndMonth');
    const startMonthValue = startMonth.find(':selected').val();
    const endMonthValue = endMonth.find(':selected').val();
    if (startMonthValue) {
        endMonth.find('option').each(function() {
            if (this.value < startMonthValue) {
                $(this).prop('disabled', true);
            } else {
                $(this).prop('disabled', false);
            }
        });
    }

    if (endMonthValue) {
        startMonth.find('option').each(function() {
            if (this.value > endMonthValue) {
                $(this).prop('disabled', true);
            } else {
                $(this).prop('disabled', false);
            }
        });
    }
}
updateMonthOptions();

$('.date-range-btn').on('click', function() {
    const buttonElement = $(this);
    const startMonth = buttonElement.data('start');
    const endMonth = buttonElement.data('end');

    if (startMonth) {
        $('#analysisStartMonth').val(startMonth);
    }
    if (endMonth) {
        $('#analysisEndMonth').val(endMonth);
    }

    updateMonthOptions();
    $('#requestAnalysis').click();

    buttonElement.css('border-width', '5px');
});
