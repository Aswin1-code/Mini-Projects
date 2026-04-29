clc;
clear;
close all;

%% Load existing dataset

data = readtable('w_m_s_final_dataset.csv');

%% Select strong + top medium players as base

strong_data = data(strcmp(data.new_label, 'STRONG'), :);
medium_data = data(strcmp(data.new_label, 'MEDIUM'), :);

% Take only high-performing medium samples
medium_filtered = medium_data( ...
    medium_data.speed > 45 & ...
    medium_data.impact > 40 & ...
    medium_data.duration < 0.60, :);

base_data = [strong_data; medium_filtered];

fprintf("Base samples used for PRO generation: %d\n", height(base_data));

%% Number of pro samples to generate

num_pro_samples = 150;

%% Initialize

pro_speed = zeros(num_pro_samples,1);
pro_impact = zeros(num_pro_samples,1);
pro_duration = zeros(num_pro_samples,1);
pro_power = zeros(num_pro_samples,1);
pro_efficiency = zeros(num_pro_samples,1);
pro_label = strings(num_pro_samples,1);

%% Generate realistic pro dataset

for i = 1:num_pro_samples

    % Randomly pick one strong player sample
    idx = randi(height(base_data));

    base_speed = base_data.speed(idx);
    base_impact = base_data.impact(idx);
    base_duration = base_data.duration(idx);

    %% Controlled realistic enhancement

    % Slight speed improvement
    speed = base_speed + rand()*6 + 2;

    % Slight impact improvement
    impact = base_impact + rand()*5 + 1.5;

    % Faster execution (lower duration)
    duration = base_duration - (rand()*0.12);

    % Safety limits
    speed = min(speed, 62);
    impact = min(impact, 52);
    duration = max(duration, 0.28);

    %% Derived features

    power = speed * impact;

    efficiency = power / (duration * 100);

    %% Store

    pro_speed(i) = round(speed,2);
    pro_impact(i) = round(impact,2);
    pro_duration(i) = round(duration,2);
    pro_power(i) = round(power,2);
    pro_efficiency(i) = round(efficiency,2);
    pro_label(i) = "PRO";

end

%% Create final table

pro_table = table( ...
    pro_speed, ...
    pro_impact, ...
    pro_duration, ...
    pro_label, ...
    pro_power, ...
    pro_efficiency, ...
    'VariableNames', { ...
    'speed', ...
    'impact', ...
    'duration', ...
    'new_label', ...
    'power', ...
    'efficiency'});

%% Save

writetable(pro_table, 'pro_benchmark_dataset.csv');

fprintf("\nPRO Benchmark Dataset Generated Successfully!\n");
fprintf("Saved as: pro_benchmark_dataset.csv\n");

disp(pro_table(1:10,:));