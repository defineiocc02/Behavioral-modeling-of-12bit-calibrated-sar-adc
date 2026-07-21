% =========================================================================
% IEEE TVLSI 论文图表生成脚本 (JSSC 标准配色版)
% =========================================================================

clc; clear; close all;

set(groot, 'defaultAxesFontName', 'Times New Roman');
set(groot, 'defaultTextFontName', 'Times New Roman');
set(groot, 'defaultAxesFontSize', 9);
set(groot, 'defaultAxesLineWidth', 1.0);
set(groot, 'defaultLineLineWidth', 1.5);
set(groot, 'defaultAxesTickDir', 'in');
set(groot, 'defaultFigureColor', 'w');

% IEEE 官方色板 — 鲜艳学术配色
cBL = [  0, 114, 189] / 255;  % blue      #0072BD
cRD = [217,  83,  25] / 255;  % orange    #D95319
cGN = [119, 172,  48] / 255;  % green     #77AC30
cYL = [237, 177,  32] / 255;  % yellow    #EDB120
cPU = [126,  47, 142] / 255;  % purple    #7E2F8E
cCY = [ 77, 190, 238] / 255;  % cyan      #4DBEEE
cBK = [  0,   0,   0] / 255;  % black
cWH = [  1,   1,   1];         % white

out_dir = fullfile(pwd, '..', 'figures');
if ~exist(out_dir, 'dir'), mkdir(out_dir); end

clr_crn = {cBL, cRD, cGN, cYL, cPU, cCY};
mkr_crn = {'o','s','^','d','p','h'};
lbl_crn = {'TT','FF','SS','SF_{-40}','SF_{35}','FS'};
nc = numel(lbl_crn);

fprintf('=== IEEE TVLSI 图表生成 (JSSC 配色) ===\n');

%% =========================== Fig.4 ===========================
fprintf('[1/4] Fig.4 PVT ... ');
fig4 = figure('Units','centimeters','Position',[2 2 8.89 5.0]);
hold on; box on;

enob_on  = [10.78, 10.64, 10.68, 10.92, 10.59, 10.77];
enob_off = [10.35, 10.36, 10.50, 10.51, 10.12, 10.37];
dE       = enob_on - enob_off;

bw = 0.35; xb = 1:nc;
% Fig.4 w/o CAAZ bars → pale sky blue
% Grid / borders → black (low alpha)
% Fig.8 Quantization pie → pale gold

b1 = bar(xb-bw/2, enob_off, bw, 'FaceColor', [0.60 0.82 0.95], 'EdgeColor',cWH,'LineWidth',0.5);
b2 = bar(xb+bw/2, enob_on,  bw, 'FaceColor', cBL, 'EdgeColor',cWH,'LineWidth',0.5);

for i = 1:nc
    text(xb(i), max(enob_on(i),enob_off(i))+0.07, ...
        sprintf('+%.2f', dE(i)), 'FontSize', 8, 'Color', cRD, ...
        'HorizontalAlignment','center', 'FontWeight','bold');
end

yline(10.5, '--', 'Color', cBK, 'LineWidth', 1.0);
text(nc+0.35, 10.47, 'target', 'FontSize', 7, 'FontAngle','italic', ...
    'HorizontalAlignment','right', 'Color', cBK);

xlim([0.4 nc+0.6]); ylim([9.8 11.5]);
xticks(xb); xticklabels(lbl_crn);
ylabel('ENOB [bit]', 'FontSize', 10); xlabel('Process Corner', 'FontSize', 10);

lg4 = legend({'With CAAZ','Without CAAZ'}, ...
    'Location','northeast', 'Box','on', 'FontSize', 7);
lg4.EdgeColor = cBK; lg4.LineWidth = 0.5;

grid on; set(gca, 'GridLineStyle',':','GridAlpha',0.15, 'GridColor', cBK);

exportgraphics(fig4, fullfile(out_dir, 'Fig4_Noise_Suppression.pdf'), ...
    'ContentType','vector','BackgroundColor','none');
close(fig4); disp('OK');

%% =========================== Fig.6 ===========================
fprintf('[2/4] Fig.6 Offset ... ');
fig6 = figure('Units','centimeters','Position',[2 2 8.89 5.0]);
hold on; box on;

vos   = [0, 2, 5];
eAvg  = [10.94, 11.13, 10.89];
eStd  = [0.12, 0.10, 0.03];

errorbar(vos, eAvg, eStd, eStd, 'o-', 'MarkerSize', 9, ...
    'MarkerFaceColor', cBL, 'MarkerEdgeColor', cWH, ...
    'Color', cBL, 'LineWidth', 2.0, 'CapSize', 6);

annotation(fig6, 'textbox', [0.40 0.16 0.56 0.18], ...
    'String', {'ENOB drop < 0.25 bit', 'at 5 mV input offset'}, ...
    'FontSize', 8, 'Color', cRD, 'FontWeight','bold', ...
    'BackgroundColor','w', 'EdgeColor', cBK, 'LineWidth', 0.6, ...
    'HorizontalAlignment','center', 'VerticalAlignment','middle', ...
    'FitBoxToText','on');

xlim([-0.5 6]); ylim([10.70 11.30]);
xticks(vos);
xlabel('Injected Input Offset [mV]', 'FontSize', 10);
ylabel('ENOB [bit]', 'FontSize', 10);
grid on; set(gca, 'GridLineStyle',':','GridAlpha',0.15, 'GridColor', cBK);

exportgraphics(fig6, fullfile(out_dir, 'Fig6_Offset_Sensitivity.pdf'), ...
    'ContentType','vector','BackgroundColor','none');
close(fig6); disp('OK');

%% =========================== Fig.7 ===========================
fprintf('[3/4] Fig.7 Time Window ... ');
fig7 = figure('Units','centimeters','Position',[2 2 8.89 5.5]);
hold on; box on;

td = [1, 2, 5, 10];
dat = [10.85,11.22,11.47,11.48; 10.78,11.15,11.39,11.40;
       10.88,11.25,11.50,11.51; 10.86,11.23,11.48,11.49;
       10.83,11.20,11.45,11.46; 10.84,11.21,11.46,11.47];

hh = gobjects(nc,1);
for i = 1:nc
    hh(i) = plot(td, dat(i,:), ['-', mkr_crn{i}], ...
        'Color', clr_crn{i}, 'LineWidth', 1.8, ...
        'MarkerSize', 7, 'MarkerFaceColor', cWH);
end

xlim([0.5 10.5]); ylim([10.6 11.7]);
xticks(td);
xlabel('Settling Time {\itt}_d [ns]', 'FontSize', 10);
ylabel('ENOB [bit]', 'FontSize', 10);
legend(hh, lbl_crn, 'Location','northoutside', ...
    'Box','on', 'FontSize', 7, 'NumColumns', 6, 'Orientation','horizontal', ...
    'EdgeColor', cBK, 'LineWidth', 0.4);
grid on; set(gca, 'GridLineStyle',':','GridAlpha',0.15, 'GridColor', cBK);

exportgraphics(fig7, fullfile(out_dir, 'Fig7_Time_Window_Sweep.pdf'), ...
    'ContentType','vector','BackgroundColor','none');
close(fig7); disp('OK');

%% =========================== Fig.8 ===========================
fprintf('[4/4] Fig.8 Pie ... ');
fig8 = figure('Units','centimeters','Position',[2 2 18 7]);

cP_Q  = [0.95 0.90 0.55];   % soft yellow (IEEE yellow tint)
cP_K  = cRD;
cP_O  = cBL;

subplot(1,2,1);
hL = pie([38.95,31.40,29.65], {'38.95%','31.40%','29.65%'});
hL(1).FaceColor = cP_Q; hL(3).FaceColor = cP_K; hL(5).FaceColor = cP_O;
for i = 2:2:6, hL(i).FontSize = 9; hL(i).FontWeight = 'bold'; hL(i).Color = cBK; end
hL(4).Color = cWH;
title('Without CAAZ Cancellation', 'FontSize', 10, 'FontWeight','bold');
xlabel({['Total Noise: 1.656{\times}10^{-7} V^2'];'SNR: 69.91 dB'}, ...
    'FontSize', 8, 'Color', cBK);

subplot(1,2,2);
hR = pie([52.49,7.60,39.91], {'52.49%','7.60%','39.91%'});
hR(1).FaceColor = cP_Q; hR(3).FaceColor = cP_K; hR(5).FaceColor = cP_O;
for i = 2:2:6, hR(i).FontSize = 9; hR(i).FontWeight = 'bold'; hR(i).Color = cBK; end
hR(4).Color = cWH;
title('With CAAZ Cancellation', 'FontSize', 10, 'FontWeight','bold');
xlabel({['Total Noise: 1.229{\times}10^{-7} V^2'];'SNR: 70.80 dB'}, ...
    'FontSize', 8, 'Color', cBK);

lg8 = legend([hL(1), hL(3), hL(5)], ...
    {'Quantization Noise','kT/C Sampling Noise','Other Circuit Noise'}, ...
    'Orientation','horizontal','Position',[0.18 0.01 0.64 0.06], ...
    'Box','off','FontSize',8);

exportgraphics(fig8, fullfile(out_dir, 'Fig8_Noise_Pie_Charts.pdf'), ...
    'ContentType','vector','BackgroundColor','none');
close(fig8); disp('OK');

fprintf('=== 完成！4 组 PDF 输出至: %s ===\n', out_dir);
