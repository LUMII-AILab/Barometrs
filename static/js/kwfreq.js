(function () {
    'use strict';

    let keywordsData = [];
    let selectedWord = null;
    let sortField = 'count';

    function getGlobalRange() {
        const form = $('#analysisRequestForm');
        const startMonth = form.find('[name="analysisStartMonth"]').val();
        const endMonth = form.find('[name="analysisEndMonth"]').val();
        const startDate = startMonth + '-01';
        const [y, m] = endMonth.split('-').map(Number);
        const lastDay = new Date(y, m, 0).getDate();
        const endDate = endMonth + '-' + String(lastDay).padStart(2, '0');
        return { startDate, endDate };
    }

    function getLang()        { return $('#kwfreqLang').val(); }
    function getWebsite()     { return $('#kwfreqWebsite').val(); }
    function getSelectedDate(){ return $('#kwfreqDate').val(); }
    function getSortVal(kw)   { return sortField === 'weight_sum' ? kw.weight_sum : kw.count; }
    function getTopN()        { const v = $('#kwfreqTopN').val(); return v === 'all' ? Infinity : parseInt(v, 10); }
    function getMinCount()    { return parseInt($('#kwfreqMinCount').val(), 10) || 0; }
    function getStyle()       { return $('#kwfreqStyle').val(); }

    function getFilteredData() {
        const minCount = getMinCount();
        const topN = getTopN();
        const filtered = keywordsData.filter(kw => kw.count >= minCount);
        filtered.sort((a, b) => getSortVal(b) - getSortVal(a));
        return topN === Infinity ? filtered : filtered.slice(0, topN);
    }

    function cloudColor(word, weight) {
        const style = getStyle();
        // weight here is font size: 14 (min) to 70 (max); t = 0 (rare) → 1 (frequent)
        const t = Math.max(0, Math.min(1, (weight - 14) / 56));
        if (style === 'mono') {
            const l = Math.round(75 - t * 60);
            return `hsl(0,0%,${l}%)`;
        }
        if (style === 'heat') {
            // orange (#e8921a) → dark red (#8b0000)
            const r = Math.round(232 - t * 93);
            const g = Math.round(146 - t * 146);
            const b = Math.round(26 - t * 26);
            return `rgb(${r},${g},${b})`;
        }
        // blue (default)
        return t > 0.5 ? '#1a5fa8' : '#4a90d9';
    }

    function loadDates() {
        const { startDate, endDate } = getGlobalRange();
        $.get('/aggressive_keywords_dates', {
            language: getLang(), startDate, endDate, website: getWebsite()
        }, function (dates) {
            const sel = $('#kwfreqDate');
            const prev = sel.val();
            sel.empty().append('<option value="all">aggregate</option>');
            dates.forEach(d => sel.append(`<option value="${d}">${d}</option>`));
            if (prev && (prev === 'all' || dates.includes(prev))) sel.val(prev);
            loadKeywords();
        });
    }

    function loadKeywords() {
        const { startDate, endDate } = getGlobalRange();
        const date = getSelectedDate();

        const isAggregate = date === 'all';
        const url = isAggregate ? '/aggressive_keywords_by_period' : '/aggressive_keywords_by_day';
        const params = isAggregate
            ? { language: getLang(), startDate, endDate, website: getWebsite() }
            : { language: getLang(), requestDate: date, website: getWebsite() };

        $.get(url, params, function (data) {
            keywordsData = data;
            selectedWord = null;
            renderList();
            renderCloud();
            resetPanels();
        });
    }

    function renderList() {
        const filtered = getFilteredData();
        const total = keywordsData.length;
        $('#kwfreqKeywordCount').text(
            filtered.length === total ? total : `${filtered.length} of ${total}`
        );
        const container = $('#kwfreqKeywordList').empty();
        filtered.forEach(kw => {
            const row = $('<div class="kwfreq-kw-row">').toggleClass('selected', kw.word === selectedWord);
            row.append($('<span class="kwfreq-kw-word">').text(kw.word));
            row.append($('<span class="kwfreq-kw-counts">').text(kw.count + ' / ' + kw.article_count));
            row.on('click', () => selectKeyword(kw));
            container.append(row);
        });
    }

    function renderCloud() {
        const canvas = document.getElementById('kwfreqWordCloud');
        const container = canvas.parentElement;
        canvas.width = container.clientWidth || 600;
        canvas.height = container.clientHeight || 500;

        const filtered = getFilteredData();
        if (!filtered.length) {
            canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
            return;
        }

        const maxVal = getSortVal(filtered[0]);
        const minVal = getSortVal(filtered[filtered.length - 1]);
        const span = maxVal - minVal || 1;

        const list = filtered.map(kw => {
            const val = getSortVal(kw);
            const size = Math.round(14 + ((val - minVal) / span) * 56);
            return [kw.word, size];
        });

        WordCloud(canvas, {
            list,
            gridSize: 8,
            weightFactor: 1,
            fontFamily: 'Arial, sans-serif',
            color: cloudColor,
            backgroundColor: '#ffffff',
            rotateRatio: 0,
            shrinkToFit: true,
        });
    }

    function selectKeyword(kw) {
        selectedWord = kw.word;
        renderList();
        renderForms(kw.forms || {});
        loadArticles(kw.word);
    }

    function renderForms(forms) {
        const panel = $('#kwfreqForms');
        const entries = Object.entries(forms).sort((a, b) => b[1] - a[1]);
        if (!entries.length) {
            panel.html('<span class="kwfreq-placeholder">No word forms found.</span>');
            return;
        }
        panel.html(entries.map(([form, cnt]) =>
            `<span class="kwfreq-form-chip">${form}<span class="kwfreq-form-cnt">${cnt}</span></span>`
        ).join(''));
    }

    function loadArticles(word) {
        const { startDate, endDate } = getGlobalRange();
        const date = getSelectedDate();
        const s = date === 'all' ? startDate : date;
        const e = date === 'all' ? endDate : date;

        $('#kwfreqArticles').html('<span class="kwfreq-placeholder">Loading...</span>');

        $.get('/aggressive_keyword_articles', {
            lemma: word, language: getLang(), startDate: s, endDate: e, website: getWebsite()
        }, function (articles) {
            const panel = $('#kwfreqArticles');
            if (!articles.length) {
                panel.html('<span class="kwfreq-placeholder">No articles found.</span>');
                return;
            }
            panel.html(articles.slice(0, 10).map(a =>
                `<div class="kwfreq-article">
                    <a href="${a.url}" target="_blank" rel="noopener">${a.headline || '—'}</a>
                    <span class="kwfreq-article-meta">${a.website} ${a.pub_timestamp || ''}</span>
                </div>`
            ).join(''));
        });
    }

    function resetPanels() {
        selectedWord = null;
        $('#kwfreqForms').html('<span class="kwfreq-placeholder">Word forms...</span>');
        $('#kwfreqArticles').html('<span class="kwfreq-placeholder">Top 10 articles...</span>');
    }

    // Re-render cloud when panel is resized
    let resizeTimer;
    new ResizeObserver(() => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => { if (keywordsData.length) renderCloud(); }, 150);
    }).observe(document.querySelector('.kwfreq-cloud-panel'));

    window.addEventListener('resize', () => {
        if (document.getElementById('kwfreqTabPane').classList.contains('show') && keywordsData.length) {
            renderCloud();
        }
    });

    // Events
    document.getElementById('kwfreq-tab').addEventListener('shown.bs.tab', loadDates);
    $('#kwfreqLang, #kwfreqWebsite').on('change', loadDates);
    $('#kwfreqDate').on('change', loadKeywords);
    $('input[name="kwfreqSort"]').on('change', function () {
        sortField = this.value;
        renderList();
        renderCloud();
    });
    // Visual controls — re-render without re-fetching
    $('#kwfreqTopN, #kwfreqStyle').on('change', function () {
        renderList();
        renderCloud();
    });
    $('#kwfreqMinCount').on('input', function () {
        renderList();
        renderCloud();
    });
    $('#requestAnalysis').on('click', function () {
        if (document.getElementById('kwfreqTabPane').classList.contains('show')) loadDates();
    });
    $('#kwfreqDownloadPng').on('click', function () {
        const canvas = document.getElementById('kwfreqWordCloud');
        const a = document.createElement('a');
        a.href = canvas.toDataURL('image/png');
        a.download = 'wordcloud.png';
        a.click();
    });
})();
