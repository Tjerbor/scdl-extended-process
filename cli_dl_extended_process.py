import glob
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import pyperclip
from colorama import just_fix_windows_console
from ffmpeg import FFmpeg
from mutagen.flac import FLAC
from send2trash import send2trash

from m4a_fix import fix_m4a_files

SETTINGS_PATH = "./.cli_dl_settings"
SETTINGS_ARCHIVE_VARIABLE_NAME = "archive_path"
SETTINGS_ARCHIVE_VARIABLE_DEFAULT_VALUE = "./Extended Mixes/archive.txt"
SETTINGS_DEFAULT_PLAYLIST_VARIABLE_NAME = "default_playlist"
SETTINGS_DOWNLOAD_INTERFACE_VARIABLE_NAME = "DL_interface"
DOWNLOAD_INTERFACES = ["scdl", "yt-dlp"]
SETTINGS_DOWNLOAD_INTERFACE_VARIABLE_DEFAULT_VALUE = DOWNLOAD_INTERFACES[1]

SETTINGS: dict

BLANK = ""


def scdl_default_download(url: str, only_original: bool = False):
    command = [
        "scdl.exe",
        "-l",
        str(url),
        "--force-metadata",
        "--original-art",
        "--original-name",
        "--auth-token",
        os.environ.get("authtoken", ""),
        "--no-playlist-folder",
        "--playlist-name-format",
        r"{title}",
        "--download-archive",
        SETTINGS[SETTINGS_ARCHIVE_VARIABLE_NAME],
    ]
    if only_original:
        command.append("--only-original")
    subprocess.run(command)


def scdl_quick_download(url: str, only_original: bool = False):
    command = [
        "scdl.exe",
        "-l",
        str(url),
        "--force-metadata",
        "--original-art",
        "--original-name",
        "--auth-token",
        os.environ.get("authtoken", ""),
        "--playlist-name-format",
        r"{title} [{id}]",
    ]
    if only_original:
        command.append("--only-original")
    subprocess.run(command)


def yt_dlp_default_download(url: str):
    subprocess.run(
        [
            "yt-dlp",
            "-u",
            "oauth",
            "-p",
            os.environ.get("authtoken", ""),
            "--embed-thumbnail",
            "--embed-metadata",
            "--windows-filenames",
            "-o",
            r"%(uploader)s [%(artist)s] %(title)s [%(id)s].%(ext)s",
            "--output-na-placeholder",
            "",
            "--download-archive",
            SETTINGS[SETTINGS_ARCHIVE_VARIABLE_NAME],
            "--no-abort-on-error",
            str(url),
        ]
    )


def yt_dlp_quick_download(url: str, is_playlist: bool):
    subprocess.run(
        [
            "yt-dlp",
            "-u",
            "oauth",
            "-p",
            os.environ.get("authtoken", ""),
            "--embed-thumbnail",
            "--embed-metadata",
            "--windows-filenames",
            "-o",
            (r"%(playlist_title)s/" if is_playlist else "")
            + r"%(uploader)s [%(artist)s] %(title)s [%(id)s].%(ext)s",
            "--output-na-placeholder",
            "",
            "--no-abort-on-error",
            str(url),
        ]
    )


def clean_archive(filepath):
    IDs = load_archive(filepath)
    save_archive(filepath, IDs)


def load_archive(filepath) -> list:
    with open(filepath, "r") as archive:
        return sorted(set(archive.read().splitlines()))


def save_archive(filepath: str, archive_IDs: list):
    with open(filepath, "w") as archive:
        archive.write("\n".join(archive_IDs) + "\n")


def convert_to_scdl_archive(filepath: str):
    def convert_help_scdl(ID: str):
        return ID.removeprefix("soundcloud ") if ID.startswith("soundlcoud ") else ID

    try:
        IDs = load_archive(filepath)
        # case yt-dlp archive
        if IDs[0].startswith("soundcloud "):
            IDs = list(map(convert_help_scdl, IDs))
            save_archive(filepath, IDs)
    except Exception as e:
        pass


def convert_to_yt_dlp_archive(filepath: str):
    def convert_help_dlp(ID: str):
        return ID if ID.startswith("soundlcoud ") else f"soundcloud {ID}"

    try:
        IDs = load_archive(filepath)
        # case yt-dlp archive
        if IDs[0].isdigit():
            IDs = list(map(convert_help_dlp, IDs))
            save_archive(filepath, IDs)
    except Exception as e:
        pass


def downscale_flac():
    flacs = glob.glob("*.flac")
    for flac in flacs:
        audio = FLAC(flac)
        if audio.info.bits_per_sample == 24:
            sample_rate = audio.info.sample_rate

            if sample_rate % 44100 == 0:
                sample_rate = 44100
            elif sample_rate % 48000 == 0:
                sample_rate = 48000

            output_filepath = f"{Path(flac).with_suffix(BLANK)}-copy.flac"
            ffmpeg = (
                FFmpeg()
                .option("n")
                .input(flac)
                .output(
                    output_filepath,
                    {"acodec": "flac", "sample_fmt": "s16", "ar": sample_rate},
                )
            )

            ffmpeg.execute()

            send2trash(flac)
            os.rename(output_filepath, flac)
            logging.info(f"{flac} downscaled.")


def convert_wav_to_flac():
    wavs = glob.glob("*.wav")
    for wav in wavs:
        flac_filepath = f"{Path(wav).with_suffix(BLANK)}.flac"
        ffmpeg = (
            FFmpeg()
            .option("n")
            .input(wav)
            .output(flac_filepath, {"acodec": "flac", "sample_fmt": "s16"})
        )

        ffmpeg.execute()
        send2trash(wav)
        logging.info(f"{wav} converted.")


def scdl_extended_process():
    # Files to ignore
    m4a_files_before_download = set(glob.glob("*.m4a"))

    default_url = SETTINGS[SETTINGS_DEFAULT_PLAYLIST_VARIABLE_NAME]

    logging.info(f"\033[96mDownloading playlist entries from {default_url}\033[0m")

    if SETTINGS[SETTINGS_DOWNLOAD_INTERFACE_VARIABLE_NAME] == "scdl":
        convert_to_scdl_archive(SETTINGS[SETTINGS_ARCHIVE_VARIABLE_NAME])
        scdl_default_download(default_url)
    elif SETTINGS[SETTINGS_DOWNLOAD_INTERFACE_VARIABLE_NAME] == "yt-dlp":
        convert_to_yt_dlp_archive(SETTINGS[SETTINGS_ARCHIVE_VARIABLE_NAME])
        yt_dlp_default_download(default_url)
        convert_to_scdl_archive(SETTINGS[SETTINGS_ARCHIVE_VARIABLE_NAME])
        scdl_default_download(default_url, only_original=True)
        clean_failed_post_process_files()

    if os.path.exists(SETTINGS[SETTINGS_ARCHIVE_VARIABLE_NAME]):
        logging.info("\033[96mCleaning archive.\033[0m")
        clean_archive(SETTINGS[SETTINGS_ARCHIVE_VARIABLE_NAME])

    logging.info("\033[96mFixing m4a files for Serato.\033[0m")
    m4a_files_after_download = set(glob.glob("*.m4a"))
    fix_m4a_files(list(m4a_files_after_download - m4a_files_before_download))

    logging.info("\033[96mDownscaling flac files.\033[0m")
    downscale_flac()
    logging.info("\033[96mConverting wav files to flac.\033[0m")
    convert_wav_to_flac()


def quick_dl(url: str):
    m4a_files_before_download = set(glob.glob("**/*.m4a", recursive=True))

    logging.info(f"\033[96mDownloading {url}\033[0m")
    if SETTINGS[SETTINGS_DOWNLOAD_INTERFACE_VARIABLE_NAME] == "scdl":
        scdl_quick_download(url)
    elif SETTINGS[SETTINGS_DOWNLOAD_INTERFACE_VARIABLE_NAME] == "yt-dlp":
        yt_dlp_quick_download(url, is_url_playlist(url))
        scdl_quick_download(url, only_original=True)
        clean_failed_post_process_files()

    logging.info("\033[96mFixing m4a files for Serato.\033[0m")
    m4a_files_after_download = set(glob.glob("**/*.m4a", recursive=True))
    fix_m4a_files(list(m4a_files_after_download - m4a_files_before_download))


def load_settings() -> dict:
    settings_dict = dict()

    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as settings_file:
            settings_data = json.load(settings_file)
            settings_dict = settings_data

    return settings_dict


def update_settings(original_settings: dict, update__settings: dict):
    original_settings.update(update__settings)

    with open(SETTINGS_PATH, "w") as settings_file:
        json.dump(original_settings, settings_file)

    return original_settings


def validate_url(url: str) -> bool:
    # Kept simple
    return url.startswith("https://soundcloud.com/") or url.startswith(
        "https://on.soundcloud.com/"
    )


def is_url_playlist(url: str) -> bool:
    return "/sets/" in url and "?in=" not in url


def clean_failed_post_process_files():
    for expr in ["].temp.mp3", "].png", "].jpg"]:
        for temp in glob.glob(f"**/*{expr}", recursive=True):
            send2trash(temp)


def main():
    global SETTINGS
    just_fix_windows_console()
    logging.basicConfig(
        stream=sys.stdout, level=logging.INFO, format="INFO: %(message)s"
    )
    clipboard = pyperclip.paste()

    settings = load_settings()
    update = dict()
    if SETTINGS_ARCHIVE_VARIABLE_NAME not in settings.keys():
        update[SETTINGS_ARCHIVE_VARIABLE_NAME] = SETTINGS_ARCHIVE_VARIABLE_DEFAULT_VALUE
    if SETTINGS_DEFAULT_PLAYLIST_VARIABLE_NAME not in settings.keys() and validate_url(
        clipboard
    ):
        update[SETTINGS_DEFAULT_PLAYLIST_VARIABLE_NAME] = clipboard
    if SETTINGS_DOWNLOAD_INTERFACE_VARIABLE_NAME not in settings.keys():
        update[SETTINGS_DOWNLOAD_INTERFACE_VARIABLE_NAME] = (
            SETTINGS_DOWNLOAD_INTERFACE_VARIABLE_DEFAULT_VALUE
        )
    if len(update) > 0:
        settings = update_settings(settings, update)

    SETTINGS = settings

    if SETTINGS[SETTINGS_DEFAULT_PLAYLIST_VARIABLE_NAME] in clipboard:
        scdl_extended_process()
    elif validate_url(clipboard):
        quick_dl(clipboard)
    else:
        scdl_extended_process()


if __name__ == "__main__":
    main()
