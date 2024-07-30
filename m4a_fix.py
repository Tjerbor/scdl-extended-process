import glob
import logging
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

from colorama import just_fix_windows_console
from ffmpeg import FFmpeg
from mutagen.mp4 import MP4
from send2trash import send2trash

SILENCE_FILE_NAME = '__silence__.m4a'
SILENCE_DURATION = 0.01
CONCAT_TXT_FILE_NAME = 'concat.txt'


def render_silence(silence_file_name: str = SILENCE_FILE_NAME, silence_duration: int | float = SILENCE_DURATION):
    ffmpeg = FFmpeg() \
        .option('y') \
        .option('f', 'lavfi') \
        .input('anullsrc=channel_layout=stereo:sample_rate=48000') \
        .option('t', silence_duration) \
        .output(silence_file_name)

    ffmpeg.execute()


def delete_silence(silence_file_name: str):
    if os.path.isfile(silence_file_name):
        os.remove(silence_file_name)
    else:
        # If it fails, inform the user.
        print(f'Error: {silence_file_name} does not exist.')


def concat_silence(audio_file_path: str, muxed_audio_file_path: str):
    def create_concat_txt(input_audio_file_path: str):
        with open(CONCAT_TXT_FILE_NAME, 'w', encoding="utf-8") as txt:
            txt.write(
                f'file \'{SILENCE_FILE_NAME}\'\nfile \'{input_audio_file_path}\''
            )

    def ffmpeg_exec(muxed_audio_file_path_concat_formatted: str):
        subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', CONCAT_TXT_FILE_NAME, '-c', 'copy',
                        muxed_audio_file_path_concat_formatted])

    if any(x in audio_file_path for x in ['\'', '\\']):
        formatted_audio_file_path = ('_' + os.path.basename(audio_file_path)
                                     .replace('\'', '').replace(' ', ''))
        formatted_muxed_audio_file_path = ('_' + os.path.basename(muxed_audio_file_path)
                                           .replace('\'', '').replace(' ', ''))
        os.rename(audio_file_path, formatted_audio_file_path)
        time.sleep(2)

        create_concat_txt(formatted_audio_file_path)
        ffmpeg_exec(formatted_muxed_audio_file_path)
        time.sleep(5)

        os.rename(formatted_audio_file_path, audio_file_path)
        os.rename(formatted_muxed_audio_file_path, muxed_audio_file_path)
    else:
        create_concat_txt(audio_file_path)
        ffmpeg_exec(muxed_audio_file_path)


def delete_concat_txt():
    Path.unlink(Path(CONCAT_TXT_FILE_NAME), missing_ok=True)


def fix_m4a_files(files: list | set, silence_duration: int | float = SILENCE_DURATION):
    render_silence(silence_duration=silence_duration)
    blank = ''

    try:
        for file in files:
            muxed_filepath = f'{Path(file).with_suffix(blank)}-copy.m4a'
            concat_silence(file, muxed_filepath)

            original_m4a = MP4(file)
            muxed_m4a = MP4(muxed_filepath)
            muxed_m4a.tags = original_m4a.tags
            muxed_m4a.save()

            send2trash(file)
            os.rename(muxed_filepath, file)
            logging.info(f'{file} \033[4m\033[1;33mfixed.\033[0m')
    except Exception:
        print(traceback.format_exc())

    # delete_concat_txt()
    delete_silence(SILENCE_FILE_NAME)


def fix_all_m4a_files_in_root(silence_duration: int | float = SILENCE_DURATION):
    fix_m4a_files(glob.glob('*.m4a'), silence_duration=silence_duration)


def main():
    just_fix_windows_console()
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='INFO: %(message)s')
    if len(sys.argv) == 1:
        fix_all_m4a_files_in_root()
    elif len(sys.argv) == 2:
        fix_all_m4a_files_in_root(float(sys.argv[1]))
    elif len(sys.argv) == 3:
        fix_m4a_files([sys.argv[1]], float(sys.argv[2]))


if __name__ == '__main__':
    main()
