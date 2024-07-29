import glob
import logging
import os
import subprocess
import sys
from logging import info
from pathlib import Path

import pyperclip
from colorama import just_fix_windows_console
from ffmpeg import FFmpeg
from mutagen.flac import FLAC
from send2trash import send2trash

from m4a_fix import fix_m4a_files

ARCHIVE_PATH = r'.\Extended Mixes\archive.txt'
BLANK = ''
DEFAULT_URL = 'https://soundcloud.com/tjerbor-fritzasnt/sets/dll'


def default_download(url: str):
    subprocess.run(['scdl.exe', '-l', str(url), '--force-metadata', '--original-name', '--auth-token',
                    os.environ.get('authtoken', ''),
                    '--no-playlist-folder', '--playlist-name-format', r'{title}', '--download-archive', ARCHIVE_PATH])


def quick_download(url: str):
    subprocess.run(['scdl.exe', '-l', str(url), '--force-metadata', '--original-name', '--auth-token',
                    os.environ.get('authtoken', ''), '--playlist-name-format', r'{title} [{id}]'])


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
            info(f'{flac} downscaled.')


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
        info(f'{wav} converted.')


def scdl_extended_process():
    # Files to ignore
    m4a_files_before_download = set(glob.glob('*.m4a'))

    info(f'\033[96mDownloading playlist entries from {DEFAULT_URL}\033[0m')
    default_download(DEFAULT_URL)
    info('\033[96mCleaning archive.\033[0m')
    clean_archive(ARCHIVE_PATH)

    info('\033[96mFixing m4a files for Serato.\033[0m')
    m4a_files_after_download = set(glob.glob('*.m4a'))
    fix_m4a_files(list(m4a_files_after_download - m4a_files_before_download))

    info('\033[96mDownscaling flac files.\033[0m')
    downscale_flac()
    info('\033[96mConverting wav files to flac.\033[0m')
    convert_wav_to_flac()


def quick_dl(url: str):
    m4a_files_before_download = set(glob.glob('**/*.m4a', recursive=True))

    info(f'\033[96mDownloading {url}\033[0m')
    quick_download(url)

    info('\033[96mFixing m4a files for Serato.\033[0m')
    m4a_files_after_download = set(glob.glob('**/*.m4a', recursive=True))
    fix_m4a_files(list(m4a_files_after_download - m4a_files_before_download))


def main():
    just_fix_windows_console()
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='INFO: %(message)s')
    clipboard = pyperclip.paste()

    if DEFAULT_URL in clipboard:
        scdl_extended_process()
    elif clipboard.startswith('https://soundcloud.com/'):
        quick_dl(clipboard)
    else:
        scdl_extended_process()


if __name__ == '__main__':
    main()
