clc;
clear;
close all;

% =========================================
% 🎯 CONFIGURATION
% =========================================
num_samples_per_class = 300;   % adjust (300 = good dataset)
fs = 100;                      % sampling frequency (Hz)

stroke_types = ["SMASH", "DROP", "CLEAR", "DRIVE"];

data = [];

% =========================================
% 🧠 FUNCTION: ADD SENSOR NOISE
% =========================================
add_noise = @(x, noise_level) x + noise_level*randn(size(x));

% =========================================
% 🔥 GENERATE DATA
% =========================================
for s = 1:length(stroke_types)

    stroke = stroke_types(s);

    for i = 1:num_samples_per_class

        t = linspace(0, 1, fs); % 1 second motion window

        % =========================================
        % 🏸 BASE PHYSICS MODELS
        % =========================================

        switch stroke

            case "SMASH"
                speed = 60 + 40*rand();
                impact = 70 + 30*rand();
                duration = 0.2 + 0.4*rand();

                ax = -speed*sin(3*pi*t) .* exp(-5*t);
                ay = speed*cos(5*pi*t) .* exp(-4*t);
                az = 2*speed*exp(-6*(t-0.2).^2);

                gx = 200*sin(10*pi*t);
                gy = 250*cos(8*pi*t);
                gz = 180*sin(12*pi*t);

            case "DROP"
                speed = 10 + 30*rand();
                impact = 10 + 25*rand();
                duration = 0.5 + 0.5*rand();

                ax = 20*sin(2*pi*t).*exp(-2*t);
                ay = 15*cos(2*pi*t).*exp(-2*t);
                az = 10*sin(3*pi*t).*exp(-3*t);

                gx = 40*sin(5*pi*t);
                gy = 35*cos(4*pi*t);
                gz = 30*sin(3*pi*t);

            case "CLEAR"
                speed = 40 + 30*rand();
                impact = 40 + 30*rand();
                duration = 0.6 + 0.6*rand();

                ax = 30*sin(2*pi*t).*exp(-2*t);
                ay = 40*cos(3*pi*t).*exp(-2*t);
                az = 60*sin(pi*t).*exp(-1.5*t);

                gx = 120*sin(6*pi*t);
                gy = 140*cos(5*pi*t);
                gz = 100*sin(4*pi*t);

            case "DRIVE"
                speed = 50 + 40*rand();
                impact = 50 + 35*rand();
                duration = 0.3 + 0.3*rand();

                ax = 80*sin(6*pi*t).*exp(-3*t);
                ay = 90*cos(7*pi*t).*exp(-3*t);
                az = 20*sin(3*pi*t);

                gx = 180*sin(12*pi*t);
                gy = 160*cos(10*pi*t);
                gz = 150*sin(8*pi*t);

        end

        % =========================================
        % 📡 ADD SENSOR NOISE (REALISM)
        % =========================================
        ax = add_noise(ax, 0.05);
        ay = add_noise(ay, 0.05);
        az = add_noise(az, 0.05);

        gx = add_noise(gx, 2);
        gy = add_noise(gy, 2);
        gz = add_noise(gz, 2);

        % =========================================
        % ⚙ DERIVED FEATURES
        % =========================================
        acc_mag = sqrt(ax.^2 + ay.^2 + az.^2);
        gyro_mag = sqrt(gx.^2 + gy.^2 + gz.^2);

        peak_acc = max(acc_mag);
        peak_gyro = max(gyro_mag);

        energy = trapz(acc_mag.^2);

        % =========================================
        % 📊 STORE ROW (summary per stroke)
        % =========================================
        row = [
            mean(ax), mean(ay), mean(az), ...
            mean(gx), mean(gy), mean(gz), ...
            mean(speed), mean(impact), mean(duration), ...
            mean(acc_mag), mean(gyro_mag), ...
            peak_acc, peak_gyro, energy, ...
            s-1 % label index
        ];

        data = [data; row];

    end
end

% =========================================
% 🏷 COLUMN NAMES
% =========================================
columns = {
    'ax','ay','az',...
    'gx','gy','gz',...
    'speed','impact','duration',...
    'acc_mag','gyro_mag',...
    'peak_acc','peak_gyro','energy',...
    'label'
};

T = array2table(data, 'VariableNames', columns);

% Convert numeric label to text
labels = ["SMASH","DROP","CLEAR","DRIVE"];
T.label = labels(T.label + 1)';

% =========================================
% 💾 SAVE CSV
% =========================================
writetable(T, 'badminton_stroke_dataset.csv');

disp("✅ Dataset generated successfully!");
disp("📁 File: badminton_stroke_dataset.csv");