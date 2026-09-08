clc;
clear;
close all;

% =====================================================
% 🏸 REALISTIC BADMINTON STROKE DATASET GENERATOR
% =====================================================

disp('==============================================');
disp('🏸 REALISTIC STROKE DATASET GENERATOR STARTED');
disp('==============================================');

% =====================================================
% CONFIGURATION
% =====================================================

num_samples_per_class = 500;

stroke_types = ["SMASH", "DROP", "CLEAR", "DRIVE"];

data = [];

output_file = ['badminton_stroke_dataset_realistic_new.csv'];

% =====================================================
% NOISE FUNCTION
% =====================================================

add_noise = @(x, n) x + n * randn(size(x));

% =====================================================
% GENERATION LOOP
% =====================================================

for s = 1:length(stroke_types)

    stroke = stroke_types(s);

    fprintf('\nGenerating %s data...\n', stroke);

    for i = 1:num_samples_per_class

        % -------------------------
        % SMASH
        % -------------------------
        if stroke == "SMASH"

            ax = add_noise(-0.2 + 0.3*rand(), 0.08);
            ay = add_noise(0.3 + 0.3*rand(), 0.08);
            az = add_noise(-1.2 - 0.8*rand(), 0.1);

            gx = add_noise(180 + 120*rand(), 15);
            gy = add_noise(-100 + 250*rand(), 20);
            gz = add_noise(-120 + 180*rand(), 20);

            speed = add_noise(45 + 8*rand(), 1.5);
            impact = add_noise(38 + 10*rand(), 1.5);
            duration = add_noise(0.45 + 0.25*rand(), 0.05);

        % -------------------------
        % DROP
        % -------------------------
        elseif stroke == "DROP"

            ax = add_noise(-0.05 + 0.1*rand(), 0.03);
            ay = add_noise(-0.4 + 0.1*rand(), 0.03);
            az = add_noise(-0.3 + 0.2*rand(), 0.04);

            gx = add_noise(-5 + 25*rand(), 5);
            gy = add_noise(-10 + 20*rand(), 4);
            gz = add_noise(-12 + 12*rand(), 4);

            speed = add_noise(10 + 10*rand(), 0.8);
            impact = add_noise(15 + 5*rand(), 0.8);
            duration = add_noise(0.20, 0.02);

        % -------------------------
        % CLEAR
        % -------------------------
        elseif stroke == "CLEAR"

            ax = add_noise(0.1 + 0.2*rand(), 0.05);
            ay = add_noise(0.2 + 0.2*rand(), 0.05);
            az = add_noise(-1.0 - 0.6*rand(), 0.08);

            gx = add_noise(90 + 80*rand(), 10);
            gy = add_noise(-60 + 120*rand(), 12);
            gz = add_noise(-70 + 100*rand(), 10);

            speed = add_noise(30 + 12*rand(), 1.2);
            impact = add_noise(25 + 8*rand(), 1.2);
            duration = add_noise(0.60 + 0.30*rand(), 0.05);

        % -------------------------
        % DRIVE
        % -------------------------
        else

            ax = add_noise(0.05 + 0.2*rand(), 0.05);
            ay = add_noise(0.05 + 0.2*rand(), 0.05);
            az = add_noise(-0.8 - 0.5*rand(), 0.07);

            gx = add_noise(110 + 90*rand(), 12);
            gy = add_noise(-70 + 140*rand(), 15);
            gz = add_noise(-80 + 120*rand(), 12);

            speed = add_noise(38 + 10*rand(), 1.2);
            impact = add_noise(28 + 8*rand(), 1.0);
            duration = add_noise(0.35 + 0.2*rand(), 0.04);
        end

        % =================================================
        % DERIVED FEATURES
        % =================================================

        acc_mag = sqrt(ax^2 + ay^2 + az^2);
        gyro_mag = sqrt(gx^2 + gy^2 + gz^2);

        peak_acc = acc_mag + rand()*0.5;
        peak_gyro = gyro_mag + rand()*10;

        power = speed * impact;
        efficiency = impact / (duration + 1e-6);
        energy = acc_mag^2 * duration;

        % =================================================
        % STORE ROW
        % =================================================

        row = {
            ax, ay, az, ...
            gx, gy, gz, ...
            speed, impact, duration, ...
            acc_mag, gyro_mag, ...
            peak_acc, peak_gyro, ...
            power, efficiency, energy, ...
            stroke
        };

        data = [data; row];
    end
end

% =====================================================
% TABLE CREATION
% =====================================================

columns = {
    'ax','ay','az', ...
    'gx','gy','gz', ...
    'speed','impact','duration', ...
    'acc_mag','gyro_mag', ...
    'peak_acc','peak_gyro', ...
    'power','efficiency','energy', ...
    'stroke'
};

T = cell2table(data, 'VariableNames', columns);

% =====================================================
% SAVE
% =====================================================

writetable(T, output_file);

disp('==============================================');
disp('✅ DATASET GENERATED SUCCESSFULLY');
disp(output_file);

disp(T(1:5,:));