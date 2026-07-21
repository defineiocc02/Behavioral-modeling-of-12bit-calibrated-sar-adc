% =========================================================================
% IEEE TCAS-II 标准 SAR ADC 图表生成脚本
% 纯MATLAB原生代码，无需额外工具箱
% =========================================================================

clc; clear; close all;

%% ==================== 全局设置（IEEE TCAS-II 强制规范） ====================
set(groot, 'defaultAxesFontName', 'Arial');
set(groot, 'defaultTextFontName', 'Arial');
set(groot, 'defaultAxesTickLabelInterpreter', 'latex');
set(groot, 'defaultLegendInterpreter', 'latex');
set(groot, 'defaultTextInterpreter', 'latex');

set(groot, 'defaultAxesFontSize', 10);
set(groot, 'defaultAxesLineWidth', 1.0);
set(groot, 'defaultLineLineWidth', 1.5);
set(groot, 'defaultAxesTickDir', 'in');
set(groot, 'defaultFigureColor', 'w');

% IEEE 官方色盲友好配色
c_blue   = [0/255, 114/255, 189/255];    % #0072BD
c_red    = [217/255, 83/255,  25/255];   % #D95319
c_green  = [119/255, 172/255, 48/255];   % #77AC30
c_gray   = [126/255, 126/255, 126/255];  % #7E7E7E
c_orange = [237/255, 177/255, 32/255];   % #EDB120

output_folder = fullfile(pwd, 'figures_tcas');
if ~exist(output_folder, 'dir')
    mkdir(output_folder);
end

fprintf('=== IEEE TCAS-II 图表生成开始 ===\n');

%% ==================== 图5：噪声源分解 (8cm × 3.5cm) ====================
fprintf('正在生成图5：噪声源分解...\n');
fig5 = figure('Units', 'centimeters', 'Position', [0 0 8 3.5], 'Resize', 'off');
hold on; grid on; box on;

enob_data = [12.00, 11.57, 11.90, 11.47];
categories = {'Quant. Only', '+Raw kT/C', '+Cancelled kT/C', 'Full System'};
bar_colors = {c_gray, c_red, c_green, c_blue};

bar_width = 0.5;
x_pos = 1:4;
for i = 1:length(enob_data)
    bar(x_pos(i), enob_data(i), bar_width, 'FaceColor', bar_colors{i}, ...
        'EdgeColor', 'white', 'LineWidth', 0.5);
end

% 设置坐标轴
xlim([0.25 4.75]);
ylim([10.8 12.2]);
set(gca, 'XTick', x_pos, 'XTickLabel', categories, ...
    'YTick', 10.8:0.2:12.2, ...
    'TickLength', [0.02 0.02], ...
    'XMinorTick', 'off', 'YMinorTick', 'off');
ylabel('ENOB [bit]', 'FontSize', 11);

% 设置网格线
ax = gca;
ax.XGrid = 'on'; ax.YGrid = 'on';
ax.GridLineStyle = '--'; ax.GridAlpha = 0.4;
ax.LineWidth = 1.0;
uistack(findobj(gca, 'Type', 'Line'), 'top');

% 绘制箭头和标注
annotation(fig5, 'arrow', [0.175 0.175], [0.365 0.460], ...
    'HeadWidth', 5, 'HeadLength', 5, 'Color', c_red, 'LineWidth', 1.0);
annotation(fig5, 'textbox', [0.15 0.47 0.12 0.05], 'String', '-0.43 bit', ...
    'FontSize', 9, 'FontName', 'Arial', 'EdgeColor', 'none', ...
    'HorizontalAlignment', 'center', 'VerticalAlignment', 'bottom');

annotation(fig5, 'arrow', [0.425 0.425], [0.600 0.520], ...
    'HeadWidth', 5, 'HeadLength', 5, 'Color', c_green, 'LineWidth', 1.0);
annotation(fig5, 'textbox', [0.40 0.53 0.12 0.05], 'String', '+0.33 bit', ...
    'FontSize', 9, 'FontName', 'Arial', 'EdgeColor', 'none', ...
    'HorizontalAlignment', 'center', 'VerticalAlignment', 'bottom');

annotation(fig5, 'arrow', [0.675 0.675], [0.520 0.365], ...
    'HeadWidth', 5, 'HeadLength', 5, 'Color', c_blue, 'LineWidth', 1.0);
annotation(fig5, 'textbox', [0.65 0.38 0.12 0.05], 'String', '-0.43 bit', ...
    'FontSize', 9, 'FontName', 'Arial', 'EdgeColor', 'none', ...
    'HorizontalAlignment', 'center', 'VerticalAlignment', 'bottom');

% 图例放在图底部外侧，2列，无边框
bar_handles = findobj(gca, 'Type', 'Bar');
lgd5 = legend(bar_handles(end:-1:1), {'Quant. Noise', 'Raw kT/C Noise', 'Cancelled kT/C', 'Other Noise'}, ...
    'Orientation', 'horizontal', 'Location', 'southoutside', ...
    'NumColumns', 2, 'Box', 'off', 'FontSize', 8);
lgd5.Position(1) = 0.5 - lgd5.Position(3)/2;

exportgraphics(fig5, fullfile(output_folder, 'Fig5_Noise_Source_Breakdown.pdf'), ...
    'ContentType', 'vector', 'BackgroundColor', 'none');
close(fig5);
fprintf('  -> Fig5 完成\n');

%% ==================== 图6：输入失调敏感度 (6cm × 4cm) ====================
fprintf('正在生成图6：输入失调敏感度...\n');
fig6 = figure('Units', 'centimeters', 'Position', [0 0 6 4], 'Resize', 'off');
hold on; grid on; box on;

offset_mv = [0, 2, 5];
enob6 = [11.47, 11.45, 11.28];
error_bar = [0.04, 0.04, 0.07];

errorbar(offset_mv, enob6, error_bar, error_bar, 'o', ...
    'MarkerSize', 8, 'MarkerFaceColor', c_blue, 'MarkerEdgeColor', 'white', ...
    'LineWidth', 0.5, 'Color', c_blue, 'CapSize', 4);

xlim([-0.5 6]);
ylim([11.1 11.7]);
set(gca, 'XTick', 0:1:5, ...
    'TickLength', [0.02 0.02], ...
    'XMinorTick', 'off', 'YMinorTick', 'off');
xlabel('Injected Input Offset [mV]', 'FontSize', 11);
ylabel('ENOB [bit]', 'FontSize', 11);

ax = gca;
ax.XGrid = 'on'; ax.YGrid = 'on';
ax.GridLineStyle = '--'; ax.GridAlpha = 0.4;
ax.LineWidth = 1.0;
uistack(findobj(gca, 'Type', 'Line'), 'top');

text(3.5, 11.18, {'ENOB Degradation < 0.25 bit'; '@ 5 mV Input Offset'}, ...
    'FontSize', 9, 'FontName', 'Arial', ...
    'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle', ...
    'BackgroundColor', 'white', 'EdgeColor', 'black', 'LineWidth', 0.5);

exportgraphics(fig6, fullfile(output_folder, 'Fig6_Offset_Sensitivity.pdf'), ...
    'ContentType', 'vector', 'BackgroundColor', 'none');
close(fig6);
fprintf('  -> Fig6 完成\n');

%% ==================== 图7：建立时间扫描 (7cm × 4.5cm) ====================
fprintf('正在生成图7：建立时间扫描...\n');
fig7 = figure('Units', 'centimeters', 'Position', [0 0 7 4.5], 'Resize', 'off');
hold on; grid on; box on;

settle_ns = [1, 2, 5, 10];

data_FF = [10.78, 11.15, 11.38, 11.40];
data_SS = [10.85, 11.25, 11.50, 11.52];
data_SF40 = [10.82, 11.22, 11.47, 11.48];
data_SF35 = [10.80, 11.20, 11.45, 11.46];
data_FS = [10.83, 11.23, 11.46, 11.47];

plot(settle_ns, data_FF,  '-s', 'MarkerSize', 7, 'MarkerFaceColor', c_blue, ...
    'MarkerEdgeColor', 'white', 'LineWidth', 0.5, 'Color', c_blue);
plot(settle_ns, data_SS,  '-^', 'MarkerSize', 7, 'MarkerFaceColor', c_red, ...
    'MarkerEdgeColor', 'white', 'LineWidth', 0.5, 'Color', c_red);
plot(settle_ns, data_SF40, '-d', 'MarkerSize', 7, 'MarkerFaceColor', c_green, ...
    'MarkerEdgeColor', 'white', 'LineWidth', 0.5, 'Color', c_green);
plot(settle_ns, data_SF35, '-o', 'MarkerSize', 7, 'MarkerFaceColor', c_orange, ...
    'MarkerEdgeColor', 'white', 'LineWidth', 0.5, 'Color', c_orange);
plot(settle_ns, data_FS,  '-*', 'MarkerSize', 7, 'MarkerFaceColor', c_gray, ...
    'MarkerEdgeColor', 'white', 'LineWidth', 0.5, 'Color', c_gray);

xlim([0.5 10.5]);
ylim([10.6 11.7]);
set(gca, 'XTick', settle_ns, ...
    'TickLength', [0.02 0.02], ...
    'XMinorTick', 'off', 'YMinorTick', 'off');
xlabel('Noise Sampling Settling Time $t_{settle}$ [ns]', 'FontSize', 11);
ylabel('ENOB [bit]', 'FontSize', 11);

ax = gca;
ax.XGrid = 'on'; ax.YGrid = 'on';
ax.GridLineStyle = '--'; ax.GridAlpha = 0.4;
ax.LineWidth = 1.0;
uistack(findobj(gca, 'Type', 'Line'), 'top');

lgd7 = legend({'FF', 'SS', 'SF$_{-40}$', 'SF$_{35}$', 'FS'}, ...
    'Orientation', 'horizontal', 'Location', 'northoutside', ...
    'NumColumns', 5, 'Box', 'off', 'FontSize', 8);
lgd7.Position(1) = 0.5 - lgd7.Position(3)/2;
lgd7.Position(2) = 0.96;

exportgraphics(fig7, fullfile(output_folder, 'Fig7_Settling_Time_Sweep.pdf'), ...
    'ContentType', 'vector', 'BackgroundColor', 'none');
close(fig7);
fprintf('  -> Fig7 完成\n');

%% ==================== 图4：PVT鲁棒性 (8cm × 4.5cm) ====================
fprintf('正在生成图4：PVT鲁棒性...\n');
fig4 = figure('Units', 'centimeters', 'Position', [0 0 8 4.5], 'Resize', 'off');
hold on; grid on; box on;

corners = {'TT', 'FF', 'SS', 'SF$_{-40}$', 'SF$_{35}$', 'FS'};
enob_no_caaz = [11.28, 11.20, 11.30, 11.29, 11.25, 11.27];
enob_with_caaz = [11.48, 11.40, 11.50, 11.49, 11.45, 11.47];

bar_width = 0.35;
x_base = 1:6;
x_no_caaz = x_base - bar_width/2;
x_with_caaz = x_base + bar_width/2;

bar(x_no_caaz, enob_no_caaz, bar_width, 'FaceColor', c_gray, ...
    'EdgeColor', 'white', 'LineWidth', 0.5);
bar(x_with_caaz, enob_with_caaz, bar_width, 'FaceColor', c_blue, ...
    'EdgeColor', 'white', 'LineWidth', 0.5);

plot([0.5 6.5], [10.5 10.5], '--k', 'LineWidth', 1.5);

for i = 1:6
    text(x_base(i), enob_with_caaz(i) + 0.08, '+0.20', ...
        'FontSize', 9, 'FontName', 'Arial', 'Color', c_red, ...
        'HorizontalAlignment', 'center', 'VerticalAlignment', 'bottom');
end

xlim([0.5 6.5]);
ylim([10.0 11.8]);
set(gca, 'XTick', x_base, 'XTickLabel', corners, ...
    'TickLength', [0.02 0.02], ...
    'XMinorTick', 'off', 'YMinorTick', 'off');
ylabel('ENOB [bit]', 'FontSize', 11);

ax = gca;
ax.XGrid = 'on'; ax.YGrid = 'on';
ax.GridLineStyle = '--'; ax.GridAlpha = 0.4;
ax.LineWidth = 1.0;
uistack(findobj(gca, 'Type', 'Line'), 'top');

lgd4 = legend({'Without CAAZ', 'With CAAZ'}, ...
    'Location', 'northeast', 'Box', 'off', 'FontSize', 9);

exportgraphics(fig4, fullfile(output_folder, 'Fig4_PVT_Robustness.pdf'), ...
    'ContentType', 'vector', 'BackgroundColor', 'none');
close(fig4);
fprintf('  -> Fig4 完成\n');

fprintf('\n=== 所有图表生成完成 ===\n');
fprintf(['输出路径: ', output_folder, '\n']);
fprintf('共生成 4 个 PDF 文件\n');
