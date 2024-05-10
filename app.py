from flask import Flask, request, send_from_directory, jsonify
import json
import numpy as np
from scipy.io.wavfile import read as wav_read
from scipy.io.wavfile import write as wav_write
import base64
from base64 import b64encode
from io import BytesIO
import sounddevice as sd
import soundfile as sf
from scipy.signal import resample
app = Flask(__name__, static_folder='static')

@app.route('/')
def index():
    return send_from_directory('views', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('views', path)

@app.route('/simulate', methods=['POST'])
def simulate():
    audio_sources = request.get_json()['audioSources']
    processed_audios = []
    max_length = 0
    highest_sample_rate = 0

    # find highest sample rate
    for source in audio_sources:
        audio_data_string = source['audioData']
        if ";base64," in audio_data_string:
            _, audio_data_string = audio_data_string.split(";base64,")
        audio_bytes = base64.b64decode(audio_data_string)
        audio_file = BytesIO(audio_bytes)
        sample_rate, _ = wav_read(audio_file)
        if sample_rate > highest_sample_rate:
            highest_sample_rate = sample_rate

    # find max length
    for source in audio_sources:
        audio_data_string = source['audioData']
        path = source['path']
        if ";base64," in audio_data_string:
            _, audio_data_string = audio_data_string.split(";base64,")
        audio_bytes = base64.b64decode(audio_data_string)
        audio_file = BytesIO(audio_bytes)
        sample_rate, audio_array = wav_read(audio_file)

        processed_audio = apply_dynamic_hrtf(audio_array, path, sample_rate)
        processed_audios.append((processed_audio, sample_rate))
        
        expected_length = int(len(processed_audio[0]) * highest_sample_rate / sample_rate)
        if expected_length > max_length:
            max_length = expected_length

    # init mixed
    mixed_audio = np.zeros((2, max_length))
    for processed_audio, sample_rate in processed_audios:
        if sample_rate != highest_sample_rate:
            num_samples = int(len(processed_audio[0]) * highest_sample_rate / sample_rate)
            resampled_audio = resample(processed_audio, num_samples, axis=1)
        else:
            resampled_audio = processed_audio

        end_idx = min(len(resampled_audio[0]), max_length)
        mixed_audio[:, :end_idx] += resampled_audio[:, :end_idx]

    # normalize
    max_amp = np.max(np.abs(mixed_audio)) if mixed_audio.size > 0 else 0
    if max_amp > 1.0:
        mixed_audio /= max_amp
    
    # play_audio(mixed_audio, highest_sample_rate)
    # mixed_audio = mixed_audio.astype(np.int16)  # Convert to int16 for WAV format
    # wav_write('mixed_output.wav', highest_sample_rate, mixed_audio.T)
    save_wav('mixed_output.wav', highest_sample_rate, mixed_audio.T)    
    with open('mixed_output.wav', "rb") as audio_file:
        encoded_audio = b64encode(audio_file.read()).decode('utf-8')
    
    response = {
        'status': 'success',
        'message': 'Audio processed and mixed',
        'audioData': 'data:audio/wav;base64,' + encoded_audio
    }
    return jsonify(response)

def save_wav(file_path, sample_rate, data):
    norm_audio = data / np.max(np.abs(data))
    int_audio = (norm_audio * 32767).astype(np.int16) #16bit

    wav_write(file_path, sample_rate, int_audio)

def apply_dynamic_hrtf(input, path, sample_rate):
    dft_size, hop_size, zero_padding = 256, 256, 256
    user_center_x = 500
    user_center_y = 500

    stft_input = stft(input, dft_size, hop_size, zero_padding, None)
    num_frames = stft_input.shape[1]

    # interpolate path to have num_frames points
    interpolated_path = interpolate_path(path, num_frames)
    degrees = coordinates_to_degrees(interpolated_path)

    left_dynamic_stft = np.zeros(stft_input.shape, dtype=complex)
    right_dynamic_stft = np.zeros(stft_input.shape, dtype=complex)

    for i in range(num_frames):        
        azimuth = degrees[i]
        elevation = 0  # 2d
        point = interpolated_path[i]
        
        # get distance from user
        distance = np.sqrt((point['x'] - user_center_x)**2 + (point['y'] - user_center_y)**2)
        # simple attenuation model
        attenuation_factor = 1 / (1 + distance / 100)

        left_hrtf, right_hrtf = load_hrtf(azimuth, elevation)

        # apply hrtfs and attenuation to current time frame
        left_dynamic_stft[:, i] = stft_input[:, i] * np.fft.rfft(left_hrtf * attenuation_factor, dft_size + zero_padding)
        right_dynamic_stft[:, i] = stft_input[:, i] * np.fft.rfft(right_hrtf * attenuation_factor, dft_size + zero_padding)
    
    left_dynamic_sound = istft(left_dynamic_stft, dft_size, hop_size, zero_padding, None)
    right_dynamic_sound = istft(right_dynamic_stft, dft_size, hop_size, zero_padding, None)
    dynamic_sound = np.vstack((left_dynamic_sound, right_dynamic_sound))
    
    return dynamic_sound

# Copied from Lab 4
def load_hrtf( ad, ed):
    # Return the HRTFs for a given azimuth and elevation
    #  function h,a,e = load_hrtf( ad, ed)
    #
    # Inputs:
    #   ad  is the azimuth to use in degrees (0 is front)
    #   ed  is the elevation to use in degrees (0 is level with ears)
    #
    # Output:
    #   l,r two 128pt arrays, first is left ear HRTF, second is right ear HRTF
    # from numpy import *


    # Path where the HRTFs are
    p = 'hrtf/compact/'

    # Get nearest available elevation
    e = max( -40, min( 90, 10*(ed//10)))

    # Get nearest available azimuth
    ad = np.remainder( ad, 360)
    if ad > 180:
        ad = ad-360
    if ad < 0:
        a = abs( ad)
        fl = 1
    else:
        a = ad
        fl = 0
    a = max( 0, min( 180, 5*(a//5)))

    # Load appropriate response
    h = np.fromfile( '%s/elev%d/H%de%.3da.dat' % (p, e, e, a), dtype='>i2').astype( 'double')/32768
    if fl:
        return h[1::2],h[::2]
    else:
        return h[::2],h[1::2]
    
def stft( input_sound, dft_size, hop_size, zero_padding, window):    
    num_frames = 1 + (len(input_sound) - dft_size) // hop_size
    freq_bins = (dft_size + zero_padding) // 2 + 1
    stft_matrix = np.zeros((freq_bins, num_frames), dtype=complex)
    # window = scipy.signal.get_window(window, dft_size) if window is not None else None

    for i in range(num_frames):
        start_idx = i * hop_size
        end_idx = start_idx + dft_size
        frame = input_sound[start_idx:end_idx]

        windowed_frame = frame * window if window is not None else frame
        stft_matrix[:, i] = np.fft.rfft(windowed_frame, dft_size + zero_padding)
    
    return stft_matrix

def istft(stft_matrix, dft_size, hop_size, zero_padding, window):
    num_frames = stft_matrix.shape[1]
    output_length = dft_size + zero_padding + (num_frames - 1) * hop_size
    x = np.zeros(output_length)
        
    if window is not None:
        window = np.sqrt(window) 

    for i in range(num_frames):
        frame = np.fft.irfft(stft_matrix[:, i], dft_size + zero_padding)
        windowed_frame = frame * window if window is not None else frame
        start_idx = i * hop_size
        end_idx = start_idx + dft_size + zero_padding   
        x[start_idx:end_idx] += windowed_frame

    return x

def interpolate_path(path, num_points):    
    interpolated_path = []
    x_values = [p['x'] for p in path]
    y_values = [p['y'] for p in path]
        
    for i in range(num_points):
        t = i / (num_points - 1)
        x = np.interp(t, np.linspace(0, 1, len(path)), x_values)
        y = np.interp(t, np.linspace(0, 1, len(path)), y_values)
        interpolated_path.append({'x': x, 'y': y})

    return interpolated_path

def coordinates_to_degrees(path):
    user_center_x = 500
    user_center_y = 500
    degrees = []

    for point in path:
        # normalize coordinates by shifting center
        dx = point['x'] - user_center_x
        dy = user_center_y - point['y']  # +y should be upwards
        
        angle_rad = np.arctan2(dy, dx)
        angle_deg = np.degrees(angle_rad)        
        
        angle_deg = (450 - angle_deg) % 360  # 450 instead of 360+90 to rotate the axis
        if angle_deg > 180:
            angle_deg -= 360

        # print(angle_deg)

        degrees.append(angle_deg)

    return degrees

def play_audio(audio, sample_rate):
    max_amp = np.max(np.abs(audio))
    normalized_audio = audio / max_amp

    sd.play(normalized_audio.T, sample_rate)
    sd.wait()

if __name__ == '__main__':
    app.run(debug=True)
