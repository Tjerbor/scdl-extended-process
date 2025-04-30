import glob
import os
import subprocess
from pathlib import Path

import mutagen
from ffmpeg import FFmpeg
from mutagen.flac import FLAC
from send2trash import send2trash

FILE_TYPES = sorted(['flac', 'm4a', 'mp3', 'ogg'])
DEFAULT_SILENCE_DURATION = 1
SILENCE_FILE_NAME = '__silence__'
CONCAT_TXT_FILE_NAME = '__concat__.txt'


def render_silence(filetype: str, silence_duration: int | float, samplerate: int, is_lossless: bool = False,
                   bitdepth: int = 16):
    ffmpeg = FFmpeg() \
        .option('y') \
        .option('f', 'lavfi') \
        .input(f'anullsrc=channel_layout=stereo:sample_rate={samplerate}') \
        .option('t', silence_duration)

    if is_lossless:
        if bitdepth == 24:
            bitdepth = 32
        ffmpeg = ffmpeg.output(f'{SILENCE_FILE_NAME}.{filetype}', {'acodec': filetype, 'sample_fmt': f's{bitdepth}'})
    else:
        ffmpeg = ffmpeg.output(f'{SILENCE_FILE_NAME}.{filetype}')

    ffmpeg.execute()


def delete_silences():
    for silence in [f'{SILENCE_FILE_NAME}.{filetype}' for filetype in FILE_TYPES]:
        if os.path.exists(silence):
            os.unlink(silence)


def concat_silence(audio_file_path: str, muxed_audio_file_path: str, is_lossless: bool = False):
    def create_concat_txt(input_audio_file_path: str):
        with open(CONCAT_TXT_FILE_NAME, 'w', encoding="utf-8") as txt:
            txt.write(
                f'file \'{SILENCE_FILE_NAME}{Path(audio_file_path).suffix}\'\nfile \'{input_audio_file_path}\''
            )

    def ffmpeg_exec(audio_file_path_concat_formatted: str,muxed_audio_file_path_concat_formatted: str):
        commands = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', CONCAT_TXT_FILE_NAME]
        if not is_lossless:
            commands.extend(['-c', 'copy'])
        else:
            commands.extend(['-i',audio_file_path_concat_formatted,'-map_metadata','1'])
        commands.append(muxed_audio_file_path_concat_formatted)
        subprocess.run(commands)

    if any(x in audio_file_path for x in ['\'', '\\']):
        formatted_audio_file_path = ('_' + os.path.basename(audio_file_path)
                                     .replace('\'', '').replace(' ', ''))
        formatted_muxed_audio_file_path = ('_' + os.path.basename(muxed_audio_file_path)
                                           .replace('\'', '').replace(' ', ''))
        os.rename(audio_file_path, formatted_audio_file_path)

        create_concat_txt(formatted_audio_file_path)
        ffmpeg_exec(formatted_audio_file_path,formatted_muxed_audio_file_path)

        os.rename(formatted_audio_file_path, audio_file_path)
        os.rename(formatted_muxed_audio_file_path, muxed_audio_file_path)
    else:
        create_concat_txt(audio_file_path)
        ffmpeg_exec(audio_file_path,muxed_audio_file_path)


def delete_concat_txt():
    Path.unlink(Path(CONCAT_TXT_FILE_NAME), missing_ok=True)


def process_flac(files: list, silence_duration: int | float):
    audios = []
    for file in files:
        audio = FLAC(file)
        audios.append([audio.info.sample_rate, audio.info.bits_per_sample, file, audio])
    audios = sorted(audios, key=lambda x: (x[0], x[1], [2]))
    smp_rt = 0
    bt_dph = 0
    for audio_details in audios:
        sample_rate, bit_depth, file_name, audio = audio_details
        if (sample_rate != smp_rt) or (bit_depth != bt_dph):
            smp_rt, bt_dph = sample_rate, bit_depth
            render_silence('flac', silence_duration, sample_rate, True, bit_depth)
        muxed_file_name = f'{Path(file_name).with_suffix('')}-copy.flac'
        concat_silence(file_name, muxed_file_name, True)
        # muxed_audio = FLAC(muxed_file_name)
        # print(audio.tags)
        # muxed_audio.tags = audio.tags
        # muxed_audio.pprint()
        # print(muxed_audio.tags)
        # muxed_audio.save(muxed_file_name)
        send2trash(file_name)
        os.rename(muxed_file_name, file_name)


def process_lossy(file_type: str,files: list, silence_duration: int | float):
    audios = []
    for file in files:
        audio = mutagen.File(file)
        audios.append([audio.info.sample_rate, file, audio])
    audios = sorted(audios, key=lambda x: (x[0], x[1]))
    print('\n'.join([str(x) for x in audios]))
    smp_rt = 0
    bt_dph = 0
    for audio_details in audios:
        sample_rate, file_name, audio = audio_details
        if sample_rate != smp_rt:
            smp_rt = sample_rate
            render_silence(file_type, silence_duration, sample_rate)
        muxed_file_name = f'{Path(file_name).with_suffix('')}-copy.{file_type}'
        concat_silence(file_name, muxed_file_name)
        muxed_audio = mutagen.File(muxed_file_name)
        muxed_audio.tags = audio.tags
        muxed_audio.save()
        send2trash(file_name)
        os.rename(muxed_file_name, file_name)


def get_all_files():
    for file_type in FILE_TYPES:
        files = glob.glob(f'*.{file_type}')

        # grouped = []
        #
        # for file_name in files:
        #     audio = mutagen.File(file_name)
        #     grouped.append([audio.info.sample_rate, file_name])
        #
        # print(grouped)
        if file_type == 'flac':
            process_flac(files, DEFAULT_SILENCE_DURATION)

    delete_silences()
    delete_concat_txt()


def main():
    raise NotImplementedError


if __name__ == '__main__':
    # main()
    # render_silence('flac', 10, 44100, True, 24)
    get_all_files()
    pass
