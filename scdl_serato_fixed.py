import glob
import logging
import os
import subprocess
import sys
import traceback
from logging import info
from pathlib import Path

from ffmpeg import FFmpeg
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from send2trash import send2trash

SILENCE_FILE_NAME = 'silence.m4a'
SILENCE_DURATION = 0.01
CONCAT_TXT_FILE_NAME = 'concat.txt'
ARCHIVE_PATH = r'.\Extended Mixes\archive.txt'
BLANK = ''
URL = 'https://soundcloud.com/tjerbor-fritzasnt/sets/dll'


def render_silence():
    ffmpeg = FFmpeg() \
        .option('y') \
        .option('f', 'lavfi') \
        .input('anullsrc=channel_layout=stereo:sample_rate=48000') \
        .option('t', SILENCE_DURATION) \
        .output(SILENCE_FILE_NAME)

    ffmpeg.execute()


def delete_silence():
    if os.path.isfile(SILENCE_FILE_NAME):
        os.remove(SILENCE_FILE_NAME)
    else:
        # If it fails, inform the user.
        print(f'Error: {SILENCE_FILE_NAME} does not exist.')


def concant_silence(original_filepath: str, muxed_filedpath: str):
    with open(CONCAT_TXT_FILE_NAME, 'w', encoding="utf-8") as txt:
        txt.write(
            f'file \'{SILENCE_FILE_NAME}\'\nfile \'{original_filepath}\''
        )

    ffmpeg = FFmpeg() \
        .option('y') \
        .option('f', 'concat') \
        .option('safe', 0) \
        .input(CONCAT_TXT_FILE_NAME) \
        .output(muxed_filedpath, c='copy')

    ffmpeg.execute()


def fix_m4a_files(files):
    render_silence()

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

    Path.unlink(Path(CONCAT_TXT_FILE_NAME), missing_ok=True)
    delete_silence()


def download(url: str):
    subprocess.run(['scdl.exe', '-l', str(url), '--force-metadata', '--original-name', '--auth-token',
                    os.environ.get('authtoken', ''),
                    '--no-playlist-folder', '--playlist-name-format', r'{title}', '--download-archive', ARCHIVE_PATH])


def clean_archive(filepath):
    with open(filepath, 'r') as archive:
        IDs = sorted(set(archive.read().splitlines()))

    with open(filepath, 'w') as archive:
        archive.write('\n'.join(IDs))


def downscale_flac():
    flacs = glob.glob('*.flac')
    for flac in flacs:
        audio = FLAC(flac)
        if audio.info.bits_per_sample == 24:
            sample_rate = audio.info.sample_rate

            if sample_rate % 44100 == 0:
                sample_rate = 44100
            elif sample_rate % 48000 == 0:
                sample_rate = 48000

            output_filepath = f'{Path(flac).with_suffix(BLANK)}-copy.flac'
            ffmpeg = FFmpeg() \
                .option('n') \
                .input(flac) \
                .output(output_filepath,
                        {'acodec': 'flac',
                         'sample_fmt': 's16',
                         'ar': sample_rate}
                        )

            ffmpeg.execute()

            send2trash(flac)
            os.rename(output_filepath, flac)


def convert_wav_to_flac():
    wavs = glob.glob('*.wav')
    for wav in wavs:
        flac_filepath = f'{Path(wav).with_suffix(BLANK)}.flac'
        ffmpeg = FFmpeg() \
            .option('n') \
            .input(wav) \
            .output(flac_filepath,
                    {'acodec': 'flac',
                     'sample_fmt': 's16'}
                    )

        ffmpeg.execute()
        send2trash(wav)


def main(url: str):
    # Files to ignore
    m4a_files_before_download = set(glob.glob('*.m4a'))

    info(f'Downloading playlist entries from {url}')
    download(url)
    info('Cleaning archive.')
    clean_archive(ARCHIVE_PATH)

    info('Fixing m4a files for Serato.')
    m4a_files_after_download = set(glob.glob('*.m4a'))
    fix_m4a_files(list(m4a_files_after_download - m4a_files_before_download))

    info('Downscaling flac files.')
    downscale_flac()
    info('Converting wav files to flac.')
    convert_wav_to_flac()


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='INFO: %(message)s')
    main(URL)
