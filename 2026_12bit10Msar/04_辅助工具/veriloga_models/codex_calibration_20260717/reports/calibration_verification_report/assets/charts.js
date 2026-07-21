/* assets/charts.js - Calibration Verification Report Charts */
(function() {
    var style = getComputedStyle(document.documentElement);
    var accent = style.getPropertyValue('--accent').trim();
    var accent2 = style.getPropertyValue('--accent2').trim();
    var ink = style.getPropertyValue('--ink').trim();
    var muted = style.getPropertyValue('--muted').trim();
    var rule = style.getPropertyValue('--rule').trim();
    var bg2 = style.getPropertyValue('--bg2').trim();

    // --- Chart 1: SNDR Comparison Bar Chart ---
    var chart1 = echarts.init(document.getElementById('chart-sndr-comparison'), null, { renderer: 'svg' });
    chart1.setOption({
        animation: false,
        title: { text: '校准前后性能对比', left: 'center', textStyle: { color: ink, fontSize: 15, fontWeight: 600 } },
        tooltip: { trigger: 'axis', appendToBody: true },
        legend: { data: ['Bypass (无校准)', 'Cal (有校准)'], bottom: 0, textStyle: { color: muted } },
        grid: { left: '8%', right: '8%', bottom: '15%', top: '12%' },
        xAxis: { type: 'category', data: ['SNDR (dB)', 'SFDR (dB)', 'ENOB (bit)', 'SNR (dB)'], axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted } },
        yAxis: [
            { type: 'value', name: 'dB', axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule, type: 'dashed' } } },
            { type: 'value', name: 'bit', min: 0, max: 12, axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted } }
        ],
        series: [
            {
                name: 'Bypass (无校准)',
                type: 'bar',
                data: [57.34, 62.99, 9.233, 57.34],
                itemStyle: { color: accent2 },
                label: { show: true, position: 'top', color: ink, fontSize: 11 }
            },
            {
                name: 'Cal (有校准)',
                type: 'bar',
                data: [68.35, 73.68, 11.062, 68.35],
                itemStyle: { color: accent },
                label: { show: true, position: 'top', color: ink, fontSize: 11 }
            }
        ]
    });
    window.addEventListener('resize', function() { chart1.resize(); });

    // --- Chart 2: Calibration Weight Comparison ---
    var chart2 = echarts.init(document.getElementById('chart-weight-comparison'), null, { renderer: 'svg' });
    chart2.setOption({
        animation: false,
        title: { text: '校准权重：期望值 vs 实测值', left: 'center', textStyle: { color: ink, fontSize: 15, fontWeight: 600 } },
        tooltip: { trigger: 'axis', appendToBody: true },
        legend: { data: ['期望权重 (wall)', '实测权重 (measured_q)'], bottom: 0, textStyle: { color: muted } },
        grid: { left: '10%', right: '8%', bottom: '15%', top: '12%' },
        xAxis: { type: 'category', data: ['C7 (t=5)', 'C9 (t=3)', 'C8 (t=4)', 'C10 (t=2)', 'C11 (t=1)', 'C12 (t=0)'], axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted } },
        yAxis: { type: 'value', name: '权重值', axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule, type: 'dashed' } } },
        series: [
            { name: '期望权重 (wall)', type: 'bar', data: [2016, 4064, 4064, 8192, 16464, 32928], itemStyle: { color: accent2 }, label: { show: true, position: 'top', color: ink, fontSize: 10 } },
            { name: '实测权重 (measured_q)', type: 'bar', data: [2048, 4112, 4096, 8272, 16464, 32880], itemStyle: { color: accent }, label: { show: true, position: 'top', color: ink, fontSize: 10 } }
        ]
    });
    window.addEventListener('resize', function() { chart2.resize(); });

    // --- Chart 3: Frequency Spectrum Comparison ---
    var chart3 = echarts.init(document.getElementById('chart-spectrum'), null, { renderer: 'svg' });

    // Bypass spectrum data (bins 1-63, magnitude)
    var bypassMag = [0.0031, 0.0015, 0.0024, 0.0037, 0.0034, 0.0049, 0.0018, 0.0011,
                     0.0041, 0.0770, 0.0020, 0.0015, 0.0012, 0.0014, 0.0021, 0.0026,
                     0.0018, 0.0016, 0.0014, 0.0022, 0.0018, 0.0021, 0.0017, 0.0028,
                     0.0021, 0.0017, 0.0016, 0.0021, 0.0018, 0.0017, 0.0020, 0.0018,
                     0.0015, 0.0020, 0.0014, 0.0022, 0.0015, 0.0020, 0.0014, 0.0025,
                     0.0018, 0.0021, 0.0022, 0.0018, 0.0019, 0.0022, 0.0017, 0.0022,
                     0.0017, 0.0032, 0.0022, 0.0028, 0.0021, 0.0017, 0.0026, 0.0031,
                     0.0024, 0.0020, 0.0021, 0.0628, 0.0019, 0.0020, 0.0017];

    // Cal spectrum data (bins 1-63, magnitude)
    var calMag = [0.0012, 0.0008, 0.0015, 0.0019, 0.0014, 0.0017, 0.0012, 0.0009,
                  0.0015, 0.0018, 0.0014, 0.0011, 0.0013, 0.0012, 0.0015, 0.0014,
                  0.0012, 0.0011, 0.0010, 0.0014, 0.0012, 0.0013, 0.0011, 0.0015,
                  0.0012, 0.0011, 0.0010, 0.0013, 0.0011, 0.0010, 0.0012, 0.0011,
                  0.0010, 0.0012, 0.0009, 0.0013, 0.0011, 0.0012, 0.0010, 0.0016,
                  0.0013, 0.0021, 0.0014, 0.0017, 0.0012, 0.0021, 0.0014, 0.0024,
                  0.0017, 0.0019, 0.0021, 0.0025, 0.0019, 0.0017, 0.0021, 0.0018,
                  0.0015, 0.0013, 0.0014, 0.0851, 0.0014, 0.0013, 0.0011];

    var binLabels = [];
    for (var i = 1; i <= 63; i++) binLabels.push('Bin ' + i);

    chart3.setOption({
        animation: false,
        title: { text: '频谱对比：Bypass vs Cal (Bin 1-63)', left: 'center', textStyle: { color: ink, fontSize: 15, fontWeight: 600 } },
        tooltip: { trigger: 'axis', appendToBody: true, formatter: function(params) {
            var s = params[0].axisValue + '<br/>';
            params.forEach(function(p) { s += p.marker + p.seriesName + ': ' + p.value.toFixed(6) + '<br/>'; });
            return s;
        }},
        legend: { data: ['Bypass', 'Cal'], bottom: 0, textStyle: { color: muted } },
        grid: { left: '8%', right: '5%', bottom: '15%', top: '12%' },
        xAxis: { type: 'category', data: binLabels, axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted, interval: 4, rotate: 45 } },
        yAxis: { type: 'log', name: '幅度', min: 0.0001, axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule, type: 'dashed' } } },
        dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100, bottom: '5%' }],
        series: [
            { name: 'Bypass', type: 'line', data: bypassMag, showSymbol: false, lineStyle: { width: 1.5, color: accent2 }, areaStyle: { opacity: 0.1 } },
            { name: 'Cal', type: 'line', data: calMag, showSymbol: false, lineStyle: { width: 1.5, color: accent } }
        ],
        markPoint: {
            data: [
                { name: '基频 Bin 59', coord: ['Bin 59', 0.0851], itemStyle: { color: accent }, label: { formatter: '基频', color: ink } }
            ]
        }
    });
    window.addEventListener('resize', function() { chart3.resize(); });

    // --- Chart 4: Capacitor Mismatch ---
    var chart4 = echarts.init(document.getElementById('chart-cap-mismatch'), null, { renderer: 'svg' });
    chart4.setOption({
        animation: false,
        title: { text: 'CDAC电容失配值对比', left: 'center', textStyle: { color: ink, fontSize: 15, fontWeight: 600 } },
        tooltip: { trigger: 'axis', appendToBody: true },
        legend: { data: ['Sandbox (理想值)', 'ADE (失配值)'], bottom: 0, textStyle: { color: muted } },
        grid: { left: '10%', right: '8%', bottom: '15%', top: '12%' },
        xAxis: { type: 'category', data: ['C12 P', 'C11 P', 'C10 P', 'C12 N', 'C11 N', 'C10 N', 'CR N'], axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted } },
        yAxis: { type: 'value', name: '电容值 (×C)', axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule, type: 'dashed' } } },
        series: [
            { name: 'Sandbox (理想值)', type: 'bar', data: [16, 8, 4, 16, 8, 4, 2], itemStyle: { color: accent2 }, label: { show: true, position: 'top', color: ink, fontSize: 10 } },
            { name: 'ADE (失配值)', type: 'bar', data: [16.054213, 8.054243, 4.0031754, 16.0365, 8.00245, 4.078, 2.0032532], itemStyle: { color: accent }, label: { show: true, position: 'top', color: ink, fontSize: 9, formatter: function(p) { return p.value.toFixed(4); } } }
        ]
    });
    window.addEventListener('resize', function() { chart4.resize(); });
})();
