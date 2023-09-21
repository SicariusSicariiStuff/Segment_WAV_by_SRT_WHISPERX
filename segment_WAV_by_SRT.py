import os
import subprocess
from pydub import AudioSegment
import pysrt
import argparse
from tqdm import tqdm
import re
import multiprocessing

def process_wav_srt_pair(wav_file, srt_file, output_dir):
    # Extract the base filename without extension for creating the output folder
    base_filename = os.path.splitext(os.path.basename(wav_file))[0]

    # Create the output directory based on the WAV file name
    output_dir = os.path.join(output_dir, f"out_{base_filename}")
    os.makedirs(output_dir, exist_ok=True)

    # Check if the temporary WAV file exists, if not, perform the conversion
    temp_wav_file = "TEMP_WAV.wav"
    if not os.path.isfile(temp_wav_file):
        print("Converting WAV file...")
        ffmpeg_command = [
            "ffmpeg",
            "-i", wav_file,
            "-acodec", "pcm_s16le",  # 16-bit PCM codec
            "-ar", "44100",          # Sample rate (adjust if needed)
            "-y",                    # Overwrite output file if it exists
            temp_wav_file
        ]

        # Use subprocess.Popen to capture ffmpeg progress
        process = subprocess.Popen(ffmpeg_command, stderr=subprocess.PIPE, universal_newlines=True)
        duration_pattern = re.compile(r"Duration: (\d+:\d+:\d+\.\d+),")
        for line in process.stderr:
            match = duration_pattern.search(line)
            if match:
                duration_str = match.group(1)
                total_duration = sum(float(x) * 60 ** i for i, x in enumerate(reversed(duration_str.split(":"))))
            if "time=" in line:
                time_str = re.search(r"time=(\d+:\d+:\d+\.\d+)", line).group(1)
                current_time = sum(float(x) * 60 ** i for i, x in enumerate(reversed(time_str.split(":"))))
                progress = current_time / total_duration * 100
                print(f"Conversion Progress: {progress:.2f}%\r", end="")
        print("\nConversion complete.")

    # Load the temporary WAV file
    audio = AudioSegment.from_file(temp_wav_file)

    def extract_segments(speaker, segments):
        speaker_dir = os.path.join(output_dir, speaker)
        os.makedirs(speaker_dir, exist_ok=True)

        for i, segment in enumerate(tqdm(segments, desc=f"Processing {speaker}")):
            start_time = segment.start
            end_time = segment.end
            start_ms = (start_time.hours * 3600 + start_time.minutes * 60 + start_time.seconds) * 1000 + start_time.milliseconds
            end_ms = (end_time.hours * 3600 + end_time.minutes * 60 + end_time.seconds) * 1000 + end_time.milliseconds
            segment_audio = audio[start_ms:end_ms]
            segment_audio.export(os.path.join(speaker_dir, f"segment_{i}.wav"), format="wav")

            # Remove the speaker label from the text
            text = segment.text.split("]:", 1)[1].strip()
            with open(os.path.join(speaker_dir, f"segment_{i}.txt"), "w") as text_file:
                text_file.write(text)

    # Parse the SRT file
    subs = pysrt.open(srt_file)

    # Extract segments for each speaker
    speakers = set()
    for sub in subs:
        speaker = sub.text.split(":")[0].strip("[]")
        speakers.add(speaker)

    for speaker in speakers:
        segments = [sub for sub in subs if sub.text.startswith(f"[{speaker}]:")]
        extract_segments(speaker, segments)

    # Delete the temporary WAV file
    os.remove(temp_wav_file)

    # Delete empty subdirectories within the output directory
    for root, dirs, files in os.walk(output_dir, topdown=False):
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)

    print("Extraction complete. Segments saved in the output directory.")
def process_all_files_in_bulk():
    # Create a multiprocessing pool
    pool = multiprocessing.Pool()

    # Create a list to store the paths of all the output directories
    output_dirs = []

    # Process all WAV and SRT files in the current directory in parallel
    for dirpath, dirnames, filenames in os.walk('.'):
        for filename in filenames:
            if filename.endswith('.wav'):
                wav_file = os.path.join(dirpath, filename)
                srt_file = os.path.join(dirpath, filename.replace('.wav', '.srt'))
                if os.path.exists(srt_file):
                    output_dir = os.path.join("bulk_output", os.path.splitext(os.path.basename(wav_file))[0])
                    output_dirs.append(output_dir)
                    pool.apply_async(process_wav_srt_pair, args=(wav_file, srt_file, output_dir))

    # Close the pool and wait for all processes to complete
    pool.close()
    pool.join()

    # Delete empty subdirectories within the output directories
    for output_dir in output_dirs:
        for root, dirs, files in os.walk(output_dir, topdown=False):
            for directory in dirs:
                dir_path = os.path.join(root, directory)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)

def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description='Segment a WAV file by SRT subtitles.')
    parser.add_argument('--all', action='store_true',
                        help='Process all WAV and SRT files in the current directory')

    # Parse command line arguments
    args, remaining_args = parser.parse_known_args()

    if args.all:
        # Process all files in parallel when --all is used
        process_all_files_in_bulk()
    else:
        # Check for regular WAV and SRT file arguments
        if len(remaining_args) == 2:
            wav_file, srt_file = remaining_args
            # Process a single pair of WAV and SRT files
            process_wav_srt_pair(wav_file, srt_file, output_dir="output")
        else:
            print("Please provide either --all to process all files or specify WAV and SRT files.")

if __name__ == "__main__":
    main()
