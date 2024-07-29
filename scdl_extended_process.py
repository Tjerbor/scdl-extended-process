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

ARCHIVE_PATH = r'.\Extended Mixes\archive.txt'
BLANK = ''
URL = 'https://soundcloud.com/tjerbor-fritzasnt/sets/dll'





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
