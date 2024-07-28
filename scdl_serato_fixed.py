import glob
import os
import subprocess
from pathlib import Path

from ffmpeg import FFmpeg, Progress
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from send2trash import send2trash

SILENCE_FILE_NAME = 'silence.m4a'
SILENCE_DURATION = 0.01
ARCHIVE_PATH = '.\\Extended Mixes\\archive.txt'
BLANK = ''


def render_silence():
    ffmpeg = FFmpeg() \
        .option('y') \
        .option('f', 'lavfi') \
        .input('anullsrc=channel_layout=stereo:sample_rate=48000') \
        .option('t', SILENCE_DURATION) \
        .output(SILENCE_FILE_NAME)

    @ffmpeg.on("progress")
    def on_progress(progress: Progress):
        print(progress)

    ffmpeg.execute()


def delete_silence():
    if os.path.isfile(SILENCE_FILE_NAME):
        os.remove(SILENCE_FILE_NAME)
    else:
        # If it fails, inform the user.
        print(f'Error: {SILENCE_FILE_NAME} does not exist.')


def concant_silence(original_filepath: str, muxed_filedpath: str):
    with open('concat.txt', 'w', encoding="utf-8") as txt:
        txt.write(
            f'file \'{SILENCE_FILE_NAME}\'\nfile \'{original_filepath}\''
        )

    ffmpeg = FFmpeg() \
        .option('y') \
        .option('f', 'concat') \
        .option('safe', 0) \
        .input(SILENCE_FILE_NAME) \
        .option('write_id3v2', 1) \
        .option('write_apetag', 1) \
        .option('write_mpeg2', 1) \
        .option('map_metadata', 1) \
        .output(muxed_filedpath, codec="copy")

    @ffmpeg.on("progress")
    def on_progress(progress: Progress):
        print(progress)

    ffmpeg.execute()


def fix_m4a_files(files):
    render_silence()

    for file in files:
        muxed_filepath = f'{Path(file).with_suffix(BLANK)}-copy.m4a'
        concant_silence(file, muxed_filepath)

        original_m4a = MP4(file)
        muxed_m4a = MP4(muxed_filepath)
        original_m4a.tags = muxed_m4a.tags
        original_m4a.save()

        send2trash(file)

    delete_silence()


def download(URL: str):
    subprocess.run(['scdl.exe', '-l', str(URL), '--force-metadata', '--original-name', '--auth-token', '%authtoken%',
                    '--no-playlist-folder', '--playlist-name-format', '{title}', '--download-archive', ARCHIVE_PATH])

    raise NotImplementedError


def clean_archive(filepath):
    with open(ARCHIVE_PATH, 'r') as archive:
        IDs = sorted(set(archive.read().splitlines()))

    with open(ARCHIVE_PATH, 'w') as archive:
        archive.write('\n'.join(IDs))


def downscale_flac():
    flacs = glob.glob('*.flac', recursive=False)
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

            @ffmpeg.on("progress")
            def on_progress(progress: Progress):
                print(progress)

            ffmpeg.execute()

            send2trash(flac)
            os.rename(output_filepath, flac)


def convert_flac_to_wav():
    wavs = glob.glob('*.wav', recursive=False)
    for wav in wavs:
        flac_filepath = f'{Path(wav).with_suffix(BLANK)}.flac'
        ffmpeg = FFmpeg() \
            .option('n') \
            .input(wav) \
            .output(flac_filepath,
                    {'acodec': 'flac',
                     'sample_fmt': 's16'}
                    )
        send2trash(wav)


def main(URL: str):
    m4a_files_before_download = set(glob.glob('*.m4a', recursive=False))
    download(URL)
    clean_archive(ARCHIVE_PATH)
    m4a_files_after_download = set(glob.glob('*.m4a', recursive=False))

    downscale_flac()
    convert_flac_to_wav()

    fix_m4a_files(list(m4a_files_after_download - m4a_files_before_download))


if __name__ == '__main__':
    # main(pyperclip.paste())
    download('s')
