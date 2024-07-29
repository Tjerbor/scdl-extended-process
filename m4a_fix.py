import glob
import os
import sys
import traceback
from pathlib import Path

from ffmpeg import FFmpeg
from mutagen.mp4 import MP4
from send2trash import send2trash

SILENCE_FILE_NAME = '__silence__.m4a'
SILENCE_DURATION = 0.01
CONCAT_TXT_FILE_NAME = 'concat.txt'
BLANK = ''


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


def concant_silence(audio_filepath: str, muxed_audio_filedpath: str):
    with open(CONCAT_TXT_FILE_NAME, 'w', encoding="utf-8") as txt:
        txt.write(
            f'file \'{SILENCE_FILE_NAME}\'\nfile \'{audio_filepath}\''
        )

    ffmpeg = FFmpeg() \
        .option('y') \
        .option('f', 'concat') \
        .option('safe', 0) \
        .input(CONCAT_TXT_FILE_NAME) \
        .output(muxed_audio_filedpath, c='copy')

    ffmpeg.execute()


def delete_concat_txt():
    Path.unlink(Path(CONCAT_TXT_FILE_NAME), missing_ok=True)


def fix_m4a_files(files: list | set, silence_duration: int | float = SILENCE_DURATION):
    render_silence(silence_duration=silence_duration)

    try:
        for file in files:
            muxed_filepath = f'{Path(file).with_suffix(BLANK)}-copy.m4a'
            concant_silence(file, muxed_filepath)

            original_m4a = MP4(file)
            muxed_m4a = MP4(muxed_filepath)
            muxed_m4a.tags = original_m4a.tags
            muxed_m4a.save()

            send2trash(file)
            os.rename(muxed_filepath, file)
    except Exception:
        print(traceback.format_exc())

    delete_concat_txt()
    delete_silence(SILENCE_FILE_NAME)


def fix_all_m4a_files_in_root(silence_duration: int | float = SILENCE_DURATION):
    fix_m4a_files(glob.glob('*.m4a'), silence_duration=silence_duration)


def main():
    if len(sys.argv) == 1:
        fix_all_m4a_files_in_root()
    elif len(sys.argv) == 2:
        fix_all_m4a_files_in_root(float(sys.argv[1]))
    elif len(sys.argv) == 3:
        fix_m4a_files([sys.argv[1]], float(sys.argv[2]))


if __name__ == '__main__':
    main()
