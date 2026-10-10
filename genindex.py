#!/usr/bin/env python3
# ---
# Copyright 2023-2026 glowinthedark
# Copyright 2026 carlosame
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and limitations under the License.
# ---
#
# - Generate index.html in a directory tree.
# - handle symlinked files and folders: displayed with custom icons
# - by default only the current folder is processed unless `-r` (`--recursive`) is specified
# - hidden files (dot files, or the hidden attribute on Windows) are skipped; use `--include-hidden` to force inclusion
# - skip specific files by regex, e.g.: `--exclude-regex "(build|node_modules|target|__pycache__)"`
# - `--generic-icons` uses one icon for all regular files instead of per-type icons
# - `--git-dates` if run inside a Git repository, uses dates from the most recent modifying commit

import argparse
import os
import re
import stat
import sys
import time
from fnmatch import fnmatch
from functools import lru_cache
from html import escape
from urllib.parse import quote
from git import Repo

DEFAULT_OUTPUT_FILE = 'index.html'

# icon id -> extensions (lowercase, without the dot)
ICON_EXTENSIONS = {
    'image': 'jpg jpeg png gif webp tiff bmp heif heic svg',
    'video': 'mp4 mov mpeg avi ogv webm mkv vob gifv 3gp',
    'audio': 'mp3 m4a aac ogg flac wav wma midi cda aiff aif caf',
    'pdf': 'pdf',
    'csv': 'csv',
    'doc': 'txt doc docx odt fodt rtf abw pages',
    'sheet': 'xls xlsx ods fods numbers',
    'ppt': 'ppt pptx odp fodp',
    'archive': 'zip gz xz tar 7z rar zst bz2 bzip arj z',
    'deb': 'deb dpkg',
    'dist': 'rpm exe flatpak appimage jar msi apk',
    'ps1': 'ps1',
    'py': 'py pyc pyo egg',
    'sh': 'sh bash com bat dll so',
    'dmg': 'dmg',
    'iso': 'iso img',
    'md': 'md mdown markdown',
    'font': 'ttf ttc otf woff woff2 eof apf',
    'go': 'go',
    'html': 'html htm php php3 asp aspx',
    'js': 'js mjs cjs',
    'css': 'css scss less',
    'json': 'json json5 jsonc',
    'ts': 'ts',
    'sql': 'sql',
    'db': 'db sqlite mdb odb',
    'email': 'eml email mailbox mbox msg',
    'cert': 'crt pem x509 cer der ca-bundle',
    'keystore': 'key keystore jks p12 pfx pub',
}
EXT_ICON = {'.' + ext: icon for icon, exts in ICON_EXTENSIONS.items() for ext in exts.split()}
NAME_ICON = {'id_rsa': 'cert', 'LICENSE': 'license', 'README': 'license'}

# icon id -> '|'-separated SVG path data (24x24 tabler icons)
ICONS = {k: ''.join(f'<path d="{d}"/>' for d in v.split('|')) for k, v in {
    'go-up': 'M18 18h-6a3 3 0 0 1 -3 -3v-10l-4 4m8 0l-4 -4',
    'symlink': 'M4 21v-4a3 3 0 0 1 3 -3h5|M9 17l3 -3l-3 -3|M14 3v4a1 1 0 0 0 1 1h4|M5 11v-6a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2h-9.5',
    'generic': 'M14 3v4a1 1 0 0 0 1 1h4|M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z',
    'license': 'M15 21h-9a3 3 0 0 1 -3 -3v-1h10v2a2 2 0 0 0 4 0v-14a2 2 0 1 1 2 2h-2m2 -4h-11a3 3 0 0 0 -3 3v11|M9 7l4 0|M9 11l4 0',
    'image': 'M15 8h.01|M3 6a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v12a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3v-12z|M3 16l5 -5c.928 -.893 2.072 -.893 3 0l5 5|M14 14l1 -1c.928 -.893 2.072 -.893 3 0l3 3',
    'video': 'M4 4m0 2a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2z|M8 4l0 16|M16 4l0 16|M4 8l4 0|M4 16l4 0|M4 12l16 0|M16 8l4 0|M16 16l4 0',
    'audio': 'M6 17m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0|M16 17m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0|M9 17l0 -13l10 0l0 13|M9 8l10 0',
    'pdf': 'M14 3v4a1 1 0 0 0 1 1h4|M5 12v-7a2 2 0 0 1 2 -2h7l5 5v4|M5 18h1.5a1.5 1.5 0 0 0 0 -3h-1.5v6|M17 18h2|M20 15h-3v6|M11 15v6h1a2 2 0 0 0 2 -2v-2a2 2 0 0 0 -2 -2h-1z',
    'csv': 'M14 3v4a1 1 0 0 0 1 1h4|M5 12v-7a2 2 0 0 1 2 -2h7l5 5v4|M7 16.5a1.5 1.5 0 0 0 -3 0v3a1.5 1.5 0 0 0 3 0|M10 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75|M16 15l2 6l2 -6',
    'doc': 'M14 3v4a1 1 0 0 0 1 1h4|M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z|M9 9l1 0|M9 13l6 0|M9 17l6 0',
    'sheet': 'M14 3v4a1 1 0 0 0 1 1h4|M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z|M8 11h8v7h-8z|M8 15h8|M11 11v7',
    'ppt': 'M9 12v-4|M15 12v-2|M12 12v-1|M3 4h18|M4 4v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-10|M12 16v4|M9 20h6',
    'archive': 'M6 20.735a2 2 0 0 1 -1 -1.735v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2h-1|M11 17a2 2 0 0 1 2 2v2a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1v-2a2 2 0 0 1 2 -2z|M11 5l-1 0|M13 7l-1 0|M11 9l-1 0|M13 11l-1 0|M11 13l-1 0|M13 15l-1 0',
    'deb': 'M12 17c-2.397 -.943 -4 -3.153 -4 -5.635c0 -2.19 1.039 -3.14 1.604 -3.595c2.646 -2.133 6.396 -.27 6.396 3.23c0 2.5 -2.905 2.121 -3.5 1.5c-.595 -.621 -1 -1.5 -.5 -2.5|M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0',
    'dist': 'M12 3l8 4.5l0 9l-8 4.5l-8 -4.5l0 -9l8 -4.5|M12 12l8 -4.5|M12 12l0 9|M12 12l-8 -4.5|M16 5.25l-8 4.5',
    'ps1': 'M4.887 20h11.868c.893 0 1.664 -.665 1.847 -1.592l2.358 -12c.212 -1.081 -.442 -2.14 -1.462 -2.366a1.784 1.784 0 0 0 -.385 -.042h-11.868c-.893 0 -1.664 .665 -1.847 1.592l-2.358 12c-.212 1.081 .442 2.14 1.462 2.366c.127 .028 .256 .042 .385 .042z|M9 8l4 4l-6 4|M12 16h3',
    'py': 'M12 9h-7a2 2 0 0 0 -2 2v4a2 2 0 0 0 2 2h3|M12 15h7a2 2 0 0 0 2 -2v-4a2 2 0 0 0 -2 -2h-3|M8 9v-4a2 2 0 0 1 2 -2h4a2 2 0 0 1 2 2v5a2 2 0 0 1 -2 2h-4a2 2 0 0 0 -2 2v5a2 2 0 0 0 2 2h4a2 2 0 0 0 2 -2v-4|M11 6l0 .01|M13 18l0 .01',
    'sh': 'M17 20h-11a3 3 0 0 1 0 -6h11a3 3 0 0 0 0 6h1a3 3 0 0 0 3 -3v-11a2 2 0 0 0 -2 -2h-10a2 2 0 0 0 -2 2v8',
    'dmg': 'M3 4m0 1a1 1 0 0 1 1 -1h16a1 1 0 0 1 1 1v14a1 1 0 0 1 -1 1h-16a1 1 0 0 1 -1 -1z|M7 8v1|M17 8v1|M12.5 4c-.654 1.486 -1.26 3.443 -1.5 9h2.5c-.19 2.867 .094 5.024 .5 7|M7 15.5c3.667 2 6.333 2 10 0',
    'iso': 'M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0|M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0|M7 12a5 5 0 0 1 5 -5|M12 17a5 5 0 0 0 5 -5',
    'md': 'M3 5m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v10a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z|M7 15v-6l2 2l2 -2v6|M14 13l2 2l2 -2m-2 2v-6',
    'font': 'M14 3v4a1 1 0 0 0 1 1h4|M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z|M11 18h2|M12 18v-7|M9 12v-1h6v1',
    'go': 'M15.695 14.305c1.061 1.06 2.953 .888 4.226 -.384c1.272 -1.273 1.444 -3.165 .384 -4.226c-1.061 -1.06 -2.953 -.888 -4.226 .384c-1.272 1.273 -1.444 3.165 -.384 4.226z|M12.68 9.233c-1.084 -.497 -2.545 -.191 -3.591 .846c-1.284 1.273 -1.457 3.165 -.388 4.226c1.07 1.06 2.978 .888 4.261 -.384a3.669 3.669 0 0 0 1.038 -1.921h-2.427|M5.5 15h-1.5|M6 9h-2|M5 12h-3',
    'html': 'M14 3v4a1 1 0 0 0 1 1h4|M5 12v-7a2 2 0 0 1 2 -2h7l5 5v4|M2 21v-6|M5 15v6|M2 18h3|M20 15v6h2|M13 21v-6l2 3l2 -3v6|M7.5 15h3|M9 15v6',
    'js': 'M14 3v4a1 1 0 0 0 1 1h4|M3 15h3v4.5a1.5 1.5 0 0 1 -3 0|M9 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75|M5 12v-7a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2h-1',
    'css': 'M14 3v4a1 1 0 0 0 1 1h4|M5 12v-7a2 2 0 0 1 2 -2h7l5 5v4|M8 16.5a1.5 1.5 0 0 0 -3 0v3a1.5 1.5 0 0 0 3 0|M11 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75|M17 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75',
    'json': 'M20 16v-8l3 8v-8|M15 8a2 2 0 0 1 2 2v4a2 2 0 1 1 -4 0v-4a2 2 0 0 1 2 -2z|M1 8h3v6.5a1.5 1.5 0 0 1 -3 0v-.5|M7 15a1 1 0 0 0 1 1h1a1 1 0 0 0 1 -1v-2a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-2a1 1 0 0 1 1 -1h1a1 1 0 0 1 1 1',
    'ts': 'M14 3v4a1 1 0 0 0 1 1h4|M5 12v-7a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2h-1|M9 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75|M3.5 15h3|M5 15v6',
    'sql': 'M14 3v4a1 1 0 0 0 1 1h4|M5 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75|M5 12v-7a2 2 0 0 1 2 -2h7l5 5v4|M18 15v6h2|M13 15a2 2 0 0 1 2 2v2a2 2 0 1 1 -4 0v-2a2 2 0 0 1 2 -2z|M14 20l1.5 1.5',
    'db': 'M12 6m-8 0a8 3 0 1 0 16 0a8 3 0 1 0 -16 0|M4 6v6a8 3 0 0 0 16 0v-6|M4 12v6a8 3 0 0 0 16 0v-6',
    'email': 'M3 7a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v10a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-10z|M3 7l9 6l9 -6',
    'cert': 'M15 15m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0|M13 17.5v4.5l2 -1.5l2 1.5v-4.5|M10 19h-5a2 2 0 0 1 -2 -2v-10c0 -1.1 .9 -2 2 -2h14a2 2 0 0 1 2 2v10a2 2 0 0 1 -1 1.73|M6 9l12 0|M6 12l3 0|M6 15l2 0',
    'keystore': 'M16.555 3.843l3.602 3.602a2.877 2.877 0 0 1 0 4.069l-2.643 2.643a2.877 2.877 0 0 1 -4.069 0l-.301 -.301l-6.558 6.558a2 2 0 0 1 -1.239 .578l-.175 .008h-1.172a1 1 0 0 1 -.993 -.883l-.007 -.117v-1.172a2 2 0 0 1 .467 -1.284l.119 -.13l.414 -.414h2v-2h2v-2l2.144 -2.144l-.301 -.301a2.877 2.877 0 0 1 0 -4.069l2.643 -2.643a2.877 2.877 0 0 1 4.069 0z|M15 9h.01',
}.items()}
FOLDER = ('<path stroke="none" fill="#ffb900" d="M9 3a1 1 0 0 1 .608 .206l.1 .087l2.706 2.707h6.586a3 3 0 0 1 '
          '2.995 2.824l.005 .176v8a3 3 0 0 1 -2.824 2.995l-.176 .005h-14a3 3 0 0 1 -2.995 -2.824l-.005 -.176v-11a3 3 '
          '0 0 1 2.824 -2.995l.176 -.005h4z"/>')
ICONS['folder'] = FOLDER
ICONS['folder-symlink'] = FOLDER + (
    '<path fill="#000" transform="scale(.16) translate(20,50)" d="M2.4 49.68C2.4 31.056 16.464 15.84 34.392 14.088V5.424'
    'c0-2.688 3.216-4.056 5.112-2.136l19.224 19.552c.408 .416 .408 1.056 0 1.472l-19.224 19.552c-1.896 1.92-5.112 .544'
    '-5.112-2.136V33.464C19.576 35.8 7.44 44.376 4.448 59.04 3.072 56.064 2.4 52.944 2.4 49.68Z"/>')

CSS = '''*{padding:0;margin:0}
path{color:#8a8a8a}
body{font-family:sans-serif;text-rendering:optimizespeed;background-color:#fff;min-height:100vh}
body,a,svg{color:#333;text-decoration:none}
a{color:#006ed3}
a:hover{color:#319cff}
header{padding:25px 5% 15px;background-color:#f2f2f2}
th:first-child,td:first-child,th:last-child,td:last-child{width:5%}
h1{font-size:20px;font-weight:normal;white-space:nowrap;overflow-x:hidden;text-overflow:ellipsis;color:#999}
main{display:block;margin:3em auto 0;border-radius:5px;box-shadow:0 2px 5px 1px rgb(0 0 0 / 5%)}
table{width:100%;border-collapse:collapse}
tr{border-bottom:1px dashed #dadada}
tbody tr:hover{background-color:#ffffec}
th,td{text-align:left;padding:10px 0}
th{padding-top:15px;padding-bottom:15px;font-size:16px;white-space:nowrap}
td{white-space:nowrap;font-size:14px}
td:nth-child(2){width:80%}
td:nth-child(3){padding:0 20px}
th:nth-child(4),td:nth-child(4){text-align:right}
td:nth-child(2) svg{position:absolute}
td .name,td .goup{word-break:break-all;overflow-wrap:break-word;white-space:pre-wrap}
td .name{margin-left:2.34em}
td .goup{margin-left:1.75em}
.i{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
tr.clickable{cursor:pointer}
tr.clickable a{display:block}
@media (max-width:600px){*{font-size:1.06rem}.hideable{display:none}td:nth-child(2){width:auto}th:nth-child(3),td:nth-child(3){padding-right:5%;text-align:right}h1{color:#000}}
@media (prefers-color-scheme:dark){body{color:#eee;background:#121212}header{color:#eee;background:#151515}tbody tr:hover{background-color:#000020}}'''

ROW = ('<tr class="file"><td></td><td><a href="{}"><svg class="i" viewBox="0 0 24 24"><use href="#{}"/></svg>'
       '<span class="name">{}</span></a></td><td data-order="{}">{}</td><td class="hideable">'
       '<time datetime="{}">{}</time></td><td class="hideable"></td></tr>\n').format

UNITS = ('KB', 'MB', 'GB', 'TB', 'PB')


def pretty_size(n):
    """Human-readable size, truncated to whole units of 1024."""
    if n < 1024:
        return '1 byte' if n == 1 else f'{n} bytes'
    i = min((n.bit_length() - 1) // 10, len(UNITS))
    return f'{n >> 10 * i} {UNITS[i - 1]}'


def last_modification_date(entry, st, repo):
    """
    Obtain the date of last modification of a file, using a Git repository if available.
    """
    modtime = st.st_mtime_ns // 1_000_000_000
    if repo is not None:
        try:
            relative_path = os.path.relpath(entry, repo.working_tree_dir)
            commit = next(repo.iter_commits(paths=relative_path, max_count=1), None)

            if commit is not None:
                # Date of the most recent commit that modified the entry
                commit_mtime = commit.committed_datetime.timestamp()
                # If we got the original modification time, preserve it
                if modtime > commit_mtime:
                    modtime = commit_mtime

        except Exception as e:
            print(f"Warning: {e}")

    return modtime


@lru_cache(maxsize=4096)  # sibling files often share an mtime second
def format_mtime(t):
    """(ISO 8601, locale) local-time strings, or ('', '-') when out of the platform's range."""
    try:
        lt = time.localtime(t)
        return time.strftime('%Y-%m-%dT%H:%M:%S', lt), time.strftime('%c', lt)
    except (OverflowError, OSError, ValueError):
        return '', '-'


def log(*args):
    print(*args, file=sys.stderr)


def render(title, icons, rows):
    defs = ''.join(f'<g id="{i}">{ICONS[i]}</g>' for i in sorted(icons))
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{CSS}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute"><defs>{defs}</defs></svg>
<header><h1>{title}</h1></header>
<main>
<div class="listing">
<table>
<thead><tr><th></th><th>Name</th><th>Size</th><th class="hideable">Modified</th><th class="hideable"></th></tr></thead>
<tbody>
<tr class="clickable"><td></td><td><a href=".."><svg class="i" viewBox="0 0 24 24"><use href="#go-up"/></svg><span class="goup">..</span></a></td><td>&mdash;</td><td class="hideable">&mdash;</td><td class="hideable"></td></tr>
{''.join(rows)}</tbody>
</table>
</div>
</main>
</body>
</html>
'''


def process_dir(path, opts, repo):
    """Write the index file of `path`; return the subdirectories to descend into."""
    output = opts.output_file.lower()
    entries, subdirs, icons = [], [], {'go-up'}
    try:
        with os.scandir(path) as it:
            for e in it:
                name = e.name
                if (name.lower() == output or (not opts.include_hidden and name[0] == '.')
                        or (opts.exclude_regex and opts.exclude_regex.search(name))):
                    continue
                try:
                    link, is_dir = e.is_symlink(), e.is_dir()
                    if opts.filter and not is_dir and not fnmatch(name, opts.filter):
                        continue
                    try:
                        st = e.stat()
                    except OSError:  # dangling symlink, symlink loop or vanished entry
                        st = None
                    if (st and not opts.include_hidden
                            and getattr(st, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_HIDDEN):
                        continue
                    # world-readable bit (always set on Windows) spares the access() syscall
                    if not link and not (st and st.st_mode & stat.S_IROTH or os.access(e.path, os.R_OK)):
                        log(f'*** WARNING *** entry {e.path} is not readable! SKIPPING!')
                        continue
                    if is_dir:
                        icon = 'folder-symlink' if link else 'folder'
                        if opts.recursive:
                            subdirs.append(e.path)
                    elif link:
                        icon = 'symlink'
                    elif opts.generic_icons or not e.is_file():
                        icon = 'generic'
                    else:
                        icon = NAME_ICON.get(name) or EXT_ICON.get(os.path.splitext(name)[1].lower(), 'generic')
                    size, size_pretty, iso, human = -1, '&mdash;', '', '-'
                    if st:
                        if stat.S_ISREG(st.st_mode):
                            size = st.st_size
                            size_pretty = pretty_size(size)
                        iso, human = format_mtime(last_modification_date(e, st, repo))
                except OSError as err:
                    log('ERROR accessing file:', err, e.path)
                    continue
                if opts.verbose:
                    log(e.path)
                icons.add(icon)
                href = quote(name + '/' if is_dir else name, errors='surrogateescape')
                entries.append((not is_dir, name, ROW(href, icon, escape(name), size, size_pretty, iso, human)))
    except OSError as err:
        log(f'cannot read dir {path}: {err}')
        return []
    entries.sort()
    index = os.path.join(path, opts.output_file)
    try:
        # surrogateescape round-trips undecodable POSIX file names byte-for-byte
        with open(index, 'w', encoding='utf-8', errors='surrogateescape') as f:
            f.write(render(escape(os.path.basename(path) or path), icons, [row for *_, row in entries]))
    except OSError as err:
        log(f'cannot create file {index}: {err}')
    return sorted(subdirs)


def type_regex(s):
    try:
        return re.compile(s) if s else None
    except re.error as e:
        raise argparse.ArgumentTypeError(f'Invalid regular expression: {e}')


def type_dir(s):
    if not os.path.isdir(s):
        raise argparse.ArgumentTypeError(f'not a directory: {s!r}')
    return os.path.abspath(s)


def git_repo(opts):
    if opts.git_dates:
        try:
            return Repo(opts.top_dir, search_parent_directories=True)
        except (Exception):
            pass
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description='''DESCRIPTION:
    Generate directory index files (recursive is OFF by default).
    Start from current dir or from folder passed as first positional argument.
    Optionally filter by file types with --filter "*.py". ''')
    parser.add_argument('top_dir', nargs='?', type=type_dir, default=os.getcwd(),
                        help='top folder from which to start generating indexes, use current folder if not specified')
    parser.add_argument('--filter', '-f',
                        help='only include files matching glob (directories are always included)')
    parser.add_argument('--output-file', '-o', metavar='filename', default=DEFAULT_OUTPUT_FILE,
                        help=f'Custom output file, by default "{DEFAULT_OUTPUT_FILE}"')
    parser.add_argument('--recursive', '-r', action='store_true',
                        help='recursively process nested dirs (FALSE by default)')
    parser.add_argument('--include-hidden', '-i', action='store_true',
                        help='include dot hidden files (FALSE by default)')
    parser.add_argument('--exclude-regex', '-x', type=type_regex,
                        help='exclude files matching regular expression')
    parser.add_argument('--generic-icons', '-g', action='store_true',
                        help='use a single generic icon for all regular files instead of per-type icons '
                             '(folders and symlinks keep their own icons); produces smaller files')
    parser.add_argument('--git-dates', '-t', action='store_true',
                        help='if run inside a Git repository, use Git commit dates if previous to fs date')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='WARNING: can take longer time with complex file tree structures on slow terminals -'
                             ' verbosely list every processed file')
    opts = parser.parse_args(argv)
    if os.path.basename(opts.output_file) != opts.output_file or opts.output_file in ('', '.', '..'):
        parser.error(f'--output-file must be a plain file name: {opts.output_file!r}')

    repo = git_repo(opts)

    # iterative DFS: no recursion limit on deep trees; `seen` breaks symlink cycles
    pending, seen = [opts.top_dir], set()
    while pending:
        path = pending.pop()
        try:
            st = os.stat(path)
        except OSError as err:
            log(f'cannot access dir {path}: {err}')
            continue
        key = (st.st_dev, st.st_ino) if st.st_ino else os.path.realpath(path)
        if key in seen:
            continue
        seen.add(key)
        if opts.verbose:
            log(f'Traversing dir {path}')
        pending.extend(reversed(process_dir(path, opts, repo)))


if __name__ == '__main__':
    main()
