#!/usr/bin/env python3
# ---
# Copyright 2023 glowinthedark
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
# - hidden files (starting with a dot) are skipped; use `--include-hidden` to force inclusion
# - skip specific files by regex, e.g.: `--exclude-regex "(build|node_modules|target|__pycache__)"`

import argparse
import datetime
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

DEFAULT_OUTPUT_FILE = 'index.html'

EXTENSION_TYPES = {
    'id_rsa': 'cert',
    'LICENSE': 'license',
    'README': 'license',
    '.jpg': 'image',
    '.jpeg': 'image',
    '.png': 'image',
    '.gif': 'image',
    '.webp': 'image',
    '.tiff': 'image',
    '.bmp': 'image',
    '.heif': 'image',
    '.heic': 'image',
    '.svg': 'image',
    '.mp4': 'video',
    '.mov': 'video',
    '.mpeg': 'video',
    '.avi': 'video',
    '.ogv': 'video',
    '.webm': 'video',
    '.mkv': 'video',
    '.vob': 'video',
    '.gifv': 'video',
    '.3gp': 'video',
    '.mp3': 'audio',
    '.m4a': 'audio',
    '.aac': 'audio',
    '.ogg': 'audio',
    '.flac': 'audio',
    '.wav': 'audio',
    '.wma': 'audio',
    '.midi': 'audio',
    '.cda': 'audio',
    '.aiff': 'audio',
    '.aif': 'audio',
    '.caf': 'audio',
    '.pdf': 'pdf',
    '.csv': 'csv',
    '.txt': 'doc',
    '.doc': 'doc',
    '.docx': 'doc',
    '.odt': 'doc',
    '.fodt': 'doc',
    '.rtf': 'doc',
    '.abw': 'doc',
    '.pages': 'doc',
    '.xls': 'sheet',
    '.xlsx': 'sheet',
    '.ods': 'sheet',
    '.fods': 'sheet',
    '.numbers': 'sheet',
    '.ppt': 'ppt',
    '.pptx': 'ppt',
    '.odp': 'ppt',
    '.fodp': 'ppt',
    '.zip': 'archive',
    '.gz': 'archive',
    '.xz': 'archive',
    '.tar': 'archive',
    '.7z': 'archive',
    '.rar': 'archive',
    '.zst': 'archive',
    '.bz2': 'archive',
    '.bzip': 'archive',
    '.arj': 'archive',
    '.z': 'archive',
    '.deb': 'deb',
    '.dpkg': 'deb',
    '.rpm': 'dist',
    '.exe': 'dist',
    '.flatpak': 'dist',
    '.appimage': 'dist',
    '.jar': 'dist',
    '.msi': 'dist',
    '.apk': 'dist',
    '.ps1': 'ps1',
    '.py': 'py',
    '.pyc': 'py',
    '.pyo': 'py',
    '.egg': 'py',
    '.sh': 'sh',
    '.bash': 'sh',
    '.com': 'sh',
    '.bat': 'sh',
    '.dll': 'sh',
    '.so': 'sh',
    '.dmg': 'dmg',
    '.iso': 'iso',
    '.img': 'iso',
    '.md': 'md',
    '.mdown': 'md',
    '.markdown': 'md',
    '.ttf': 'font',
    '.ttc': 'font',
    '.otf': 'font',
    '.woff': 'font',
    '.woff2': 'font',
    '.eof': 'font',
    '.apf': 'font',
    '.go': 'go',
    '.html': 'html',
    '.htm': 'html',
    '.php': 'html',
    '.php3': 'html',
    '.asp': 'html',
    '.aspx': 'html',
    '.css': 'css',
    '.scss': 'css',
    '.less': 'css',
    '.json': 'json',
    '.json5': 'json',
    '.jsonc': 'json',
    '.ts': 'ts',
    '.sql': 'sql',
    '.db': 'db',
    '.sqlite': 'db',
    '.mdb': 'db',
    '.odb': 'db',
    '.eml': 'email',
    '.email': 'email',
    '.mailbox': 'email',
    '.mbox': 'email',
    '.msg': 'email',
    '.crt': 'cert',
    '.pem': 'cert',
    '.x509': 'cert',
    '.cer': 'cert',
    '.der': 'cert',
    '.ca-bundle': 'cert',
    '.key': 'keystore',
    '.keystore': 'keystore',
    '.jks': 'keystore',
    '.p12': 'keystore',
    '.pfx': 'keystore',
    '.pub': 'keystore',
    'symlink': 'symlink',
    'generic': 'generic'
}


def process_dir(top_dir, opts):
    glob_patt = opts.filter or '*'

    path_top_dir = Path(top_dir)

    index_path = Path(path_top_dir, opts.output_file)

    if opts.verbose:
        print(f'Traversing dir {path_top_dir.absolute()}')

    try:
        index_file = open(index_path, 'w')
    except Exception as e:
        print('cannot create file %s %s' % (index_path, e))
        return

    index_file.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    * { padding: 0; margin: 0; }
    
    path_FIXME {
        color: #ffb900 !important;
    }    
    path {
        color: #8a8a8a;
    }

    body {
        font-family: sans-serif;
        text-rendering: optimizespeed;
        background-color: #ffffff;
        min-height: 100vh;
    }
    
    body,
    a,
    svg,
    .layout.current,
    .layout.current svg,
    .go-up {
        color: #333;
        text-decoration: none;
    }

    a {
        color: #006ed3;
        text-decoration: none;
    }

    a:hover,
    h1 a:hover {
        color: #319cff;
    }

    header,
    #summary {
        padding-left: 5%;
        padding-right: 5%;
    }

    th:first-child,
    td:first-child {
        width: 5%;
    }

    th:last-child,
    td:last-child {
        width: 5%;
    }

    header {
        padding-top: 25px;
        padding-bottom: 15px;
        background-color: #f2f2f2;
    }

    h1 {
        font-size: 20px;
        font-weight: normal;
        white-space: nowrap;
        overflow-x: hidden;
        text-overflow: ellipsis;
        color: #999;
    }

    h1 a {
        color: #000;
        margin: 0 4px;
    }

    h1 a:hover {
        text-decoration: underline;
    }

    h1 a:first-child {
        margin: 0;
    }

    main {
        display: block;
        margin: 3em auto 0;
        border-radius: 5px;
        box-shadow: 0 2px 5px 1px rgb(0 0 0 / 5%);
    }

    .meta {
        font-size: 12px;
        font-family: Verdana, sans-serif;
        border-bottom: 1px solid #9C9C9C;
        padding-top: 10px;
        padding-bottom: 10px;
    }

    .meta-item {
        margin-right: 1em;
    }

    #filter {
        padding: 4px;
        border: 1px solid #CCC;
    }

    table {
        width: 100%;
        border-collapse: collapse;
    }

    tr {
        border-bottom: 1px dashed #dadada;
    }

    tbody tr:hover {
        background-color: #ffffec;
    }

    th,
    td {
        text-align: left;
        padding: 10px 0;
    }

    th {
        padding-top: 15px;
        padding-bottom: 15px;
        font-size: 16px;
        white-space: nowrap;
    }

    th a {
        color: black;
    }

    th svg {
        vertical-align: middle;
        z-index: 1;
    }
    

    td {
        white-space: nowrap;
        font-size: 14px;
    }

    td:nth-child(2) {
        width: 80%;
    }

    td:nth-child(3) {
        padding: 0 20px 0 20px;
    }

    th:nth-child(4),
    td:nth-child(4) {
        text-align: right;
    }

    td:nth-child(2) svg {
        position: absolute;
    }

    td .name {
        margin-left: 2.34em;
        word-break: break-all;
        overflow-wrap: break-word;
        white-space: pre-wrap;
    }

    td .goup {
        margin-left: 1.75em;
        padding: 0;
        word-break: break-all;
        overflow-wrap: break-word;
        white-space: pre-wrap;
    }

    .icon {
        margin-right: 5px;
    }

    tr.clickable { 
        cursor: pointer; 
    } 
    tr.clickable a { 
        display: block; 
    } 
    
    .folder-filled {
        color: #ffb900 !important;
    }

    @media (max-width: 600px) {

        * {
            font-size: 1.06rem;
        }
        .hideable {
            display: none;
        }

        td:nth-child(2) {
            width: auto;
        }

        th:nth-child(3),
        td:nth-child(3) {
            padding-right: 5%;
            text-align: right;
        }

        h1 {
            color: #000;
        }

        h1 a {
            margin: 0;
        }

        #filter {
            max-width: 100px;
        }
    }

    @media (prefers-color-scheme: dark) {
        body {
            color: #eee;
            background: #121212;
        }

        header {
            color: #eee;
            background: #151515;
       }

        tbody tr:hover {
            background-color: #000020;
        }
    }
    </style>
</head>
<body>
<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round" style="color: red;">
<defs>
<g id="go-up">
    <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
    <path d="M18 18h-6a3 3 0 0 1 -3 -3v-10l-4 4m8 0l-4 -4"></path>
</g>

<g id="folder">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M9 3a1 1 0 0 1 .608 .206l.1 .087l2.706 2.707h6.586a3 3 0 0 1 2.995 2.824l.005 .176v8a3 3 0 0 1 -2.824 2.995l-.176 .005h-14a3 3 0 0 1 -2.995 -2.824l-.005 -.176v-11a3 3 0 0 1 2.824 -2.995l.176 -.005h4z" stroke-width="0" fill="#ffb900"></path>
</g>

<g id="folder-symlink">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M9 3a1 1 0 0 1 .608 .206l.1 .087l2.706 2.707h6.586a3 3 0 0 1 2.995 2.824l.005 .176v8a3 3 0 0 1 -2.824 2.995l-.176 .005h-14a3 3 0 0 1 -2.995 -2.824l-.005 -.176v-11a3 3 0 0 1 2.824 -2.995l.176 -.005h4z" stroke-width="0" fill="#ffb900"></path>
  <path
  fill="#000000"
  d="M 2.4,49.68 C 2.4,31.056 16.464,15.84 34.392,14.088 V 5.424 c 0,-2.688 3.216,-4.056 5.112,-2.136 l 19.224,19.552 c 0.408,0.416 0.408,1.056 0,1.472 l -19.224,19.552 c -1.896,1.92 -5.112,0.544 -5.112,-2.136 V 33.464 C 19.576,35.8 7.44,44.376 4.448,59.04 3.072,56.064 2.4,52.944 2.4,49.68 Z"
  id="path1"
  transform="scale(0.16) translate(20,50)"/>
</g>

<g id="symlink">
 <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
 <path d="M4 21v-4a3 3 0 0 1 3 -3h5"></path>
 <path d="M9 17l3 -3l-3 -3"></path>
 <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
 <path d="M5 11v-6a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2h-9.5"></path>
</g>

<g id="generic">
 <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
 <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
 <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"></path>
</g>

<g id="license">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M15 21h-9a3 3 0 0 1 -3 -3v-1h10v2a2 2 0 0 0 4 0v-14a2 2 0 1 1 2 2h-2m2 -4h-11a3 3 0 0 0 -3 3v11"></path>
  <path d="M9 7l4 0"></path>
  <path d="M9 11l4 0"></path>
</g>

<g id="image">
   <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
   <path d="M15 8h.01"></path>
   <path d="M3 6a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v12a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3v-12z"></path>
   <path d="M3 16l5 -5c.928 -.893 2.072 -.893 3 0l5 5"></path>
   <path d="M14 14l1 -1c.928 -.893 2.072 -.893 3 0l3 3"></path>
  </g>

<g id="video">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M4 4m0 2a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2z"></path>
  <path d="M8 4l0 16"></path>
  <path d="M16 4l0 16"></path>
  <path d="M4 8l4 0"></path>
  <path d="M4 16l4 0"></path>
  <path d="M4 12l16 0"></path>
  <path d="M16 8l4 0"></path>
  <path d="M16 16l4 0"></path>
</g>

<g id="audio">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M6 17m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"></path>
  <path d="M16 17m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"></path>
  <path d="M9 17l0 -13l10 0l0 13"></path>
  <path d="M9 8l10 0"></path>
</g>

<g id="pdf">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M5 12v-7a2 2 0 0 1 2 -2h7l5 5v4"></path>
  <path d="M5 18h1.5a1.5 1.5 0 0 0 0 -3h-1.5v6"></path>
  <path d="M17 18h2"></path>
  <path d="M20 15h-3v6"></path>
  <path d="M11 15v6h1a2 2 0 0 0 2 -2v-2a2 2 0 0 0 -2 -2h-1z"></path>
</g>

<g id="csv">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M5 12v-7a2 2 0 0 1 2 -2h7l5 5v4"></path>
  <path d="M7 16.5a1.5 1.5 0 0 0 -3 0v3a1.5 1.5 0 0 0 3 0"></path>
  <path d="M10 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75"></path>
  <path d="M16 15l2 6l2 -6"></path>
</g>

<g id="doc">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"></path>
  <path d="M9 9l1 0"></path>
  <path d="M9 13l6 0"></path>
  <path d="M9 17l6 0"></path>
</g>

<g id="sheet">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"></path>
  <path d="M8 11h8v7h-8z"></path>
  <path d="M8 15h8"></path>
  <path d="M11 11v7"></path>
</g>

<g id="ppt">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M9 12v-4"></path>
  <path d="M15 12v-2"></path>
  <path d="M12 12v-1"></path>
  <path d="M3 4h18"></path>
  <path d="M4 4v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-10"></path>
  <path d="M12 16v4"></path>
  <path d="M9 20h6"></path>
</g>

<g id="archive">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M6 20.735a2 2 0 0 1 -1 -1.735v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2h-1"></path>
  <path d="M11 17a2 2 0 0 1 2 2v2a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1v-2a2 2 0 0 1 2 -2z"></path>
  <path d="M11 5l-1 0"></path>
  <path d="M13 7l-1 0"></path>
  <path d="M11 9l-1 0"></path>
  <path d="M13 11l-1 0"></path>
  <path d="M11 13l-1 0"></path>
  <path d="M13 15l-1 0"></path>
</g>

<g id="deb">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M12 17c-2.397 -.943 -4 -3.153 -4 -5.635c0 -2.19 1.039 -3.14 1.604 -3.595c2.646 -2.133 6.396 -.27 6.396 3.23c0 2.5 -2.905 2.121 -3.5 1.5c-.595 -.621 -1 -1.5 -.5 -2.5"></path>
  <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"></path>
</g>

<g id="dist">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M12 3l8 4.5l0 9l-8 4.5l-8 -4.5l0 -9l8 -4.5"></path>
  <path d="M12 12l8 -4.5"></path>
  <path d="M12 12l0 9"></path>
  <path d="M12 12l-8 -4.5"></path>
  <path d="M16 5.25l-8 4.5"></path>
</g>

<g id="ps1">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M4.887 20h11.868c.893 0 1.664 -.665 1.847 -1.592l2.358 -12c.212 -1.081 -.442 -2.14 -1.462 -2.366a1.784 1.784 0 0 0 -.385 -.042h-11.868c-.893 0 -1.664 .665 -1.847 1.592l-2.358 12c-.212 1.081 .442 2.14 1.462 2.366c.127 .028 .256 .042 .385 .042z"></path>
  <path d="M9 8l4 4l-6 4"></path>
  <path d="M12 16h3"></path>
</g>

<g id="py">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M12 9h-7a2 2 0 0 0 -2 2v4a2 2 0 0 0 2 2h3"></path>
  <path d="M12 15h7a2 2 0 0 0 2 -2v-4a2 2 0 0 0 -2 -2h-3"></path>
  <path d="M8 9v-4a2 2 0 0 1 2 -2h4a2 2 0 0 1 2 2v5a2 2 0 0 1 -2 2h-4a2 2 0 0 0 -2 2v5a2 2 0 0 0 2 2h4a2 2 0 0 0 2 -2v-4"></path>
  <path d="M11 6l0 .01"></path>
  <path d="M13 18l0 .01"></path>
</g>

<g id="sh">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M17 20h-11a3 3 0 0 1 0 -6h11a3 3 0 0 0 0 6h1a3 3 0 0 0 3 -3v-11a2 2 0 0 0 -2 -2h-10a2 2 0 0 0 -2 2v8"></path>
</g>

<g id="dmg">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M3 4m0 1a1 1 0 0 1 1 -1h16a1 1 0 0 1 1 1v14a1 1 0 0 1 -1 1h-16a1 1 0 0 1 -1 -1z"></path>
  <path d="M7 8v1"></path>
  <path d="M17 8v1"></path>
  <path d="M12.5 4c-.654 1.486 -1.26 3.443 -1.5 9h2.5c-.19 2.867 .094 5.024 .5 7"></path>
  <path d="M7 15.5c3.667 2 6.333 2 10 0"></path>
</g>

<g id="iso">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"></path>
  <path d="M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"></path>
  <path d="M7 12a5 5 0 0 1 5 -5"></path>
  <path d="M12 17a5 5 0 0 0 5 -5"></path>
</g>

<g id="md">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M3 5m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v10a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z"></path>
  <path d="M7 15v-6l2 2l2 -2v6"></path>
  <path d="M14 13l2 2l2 -2m-2 2v-6"></path>
</g>

<g id="font">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"></path>
  <path d="M11 18h2"></path>
  <path d="M12 18v-7"></path>
  <path d="M9 12v-1h6v1"></path>
</g>

<g id="go">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M15.695 14.305c1.061 1.06 2.953 .888 4.226 -.384c1.272 -1.273 1.444 -3.165 .384 -4.226c-1.061 -1.06 -2.953 -.888 -4.226 .384c-1.272 1.273 -1.444 3.165 -.384 4.226z"></path>
  <path d="M12.68 9.233c-1.084 -.497 -2.545 -.191 -3.591 .846c-1.284 1.273 -1.457 3.165 -.388 4.226c1.07 1.06 2.978 .888 4.261 -.384a3.669 3.669 0 0 0 1.038 -1.921h-2.427"></path>
  <path d="M5.5 15h-1.5"></path>
  <path d="M6 9h-2"></path>
  <path d="M5 12h-3"></path>
</g>

<g id="html">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M5 12v-7a2 2 0 0 1 2 -2h7l5 5v4"></path>
  <path d="M2 21v-6"></path>
  <path d="M5 15v6"></path>
  <path d="M2 18h3"></path>
  <path d="M20 15v6h2"></path>
  <path d="M13 21v-6l2 3l2 -3v6"></path>
  <path d="M7.5 15h3"></path>
  <path d="M9 15v6"></path>
</g>

<g id="js">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M3 15h3v4.5a1.5 1.5 0 0 1 -3 0"></path>
  <path d="M9 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75"></path>
  <path d="M5 12v-7a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2h-1"></path>
</g>

<g id="css">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M5 12v-7a2 2 0 0 1 2 -2h7l5 5v4"></path>
  <path d="M8 16.5a1.5 1.5 0 0 0 -3 0v3a1.5 1.5 0 0 0 3 0"></path>
  <path d="M11 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75"></path>
  <path d="M17 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75"></path>
</g>

<g id="json">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M20 16v-8l3 8v-8"></path>
  <path d="M15 8a2 2 0 0 1 2 2v4a2 2 0 1 1 -4 0v-4a2 2 0 0 1 2 -2z"></path>
  <path d="M1 8h3v6.5a1.5 1.5 0 0 1 -3 0v-.5"></path>
  <path d="M7 15a1 1 0 0 0 1 1h1a1 1 0 0 0 1 -1v-2a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-2a1 1 0 0 1 1 -1h1a1 1 0 0 1 1 1"></path>
</g>

<g id="ts">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M5 12v-7a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2h-1"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M9 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75"></path>
  <path d="M3.5 15h3"></path>
  <path d="M5 15v6"></path>
</g>

<g id="sql">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
  <path d="M5 20.25c0 .414 .336 .75 .75 .75h1.25a1 1 0 0 0 1 -1v-1a1 1 0 0 0 -1 -1h-1a1 1 0 0 1 -1 -1v-1a1 1 0 0 1 1 -1h1.25a.75 .75 0 0 1 .75 .75"></path>
  <path d="M5 12v-7a2 2 0 0 1 2 -2h7l5 5v4"></path>
  <path d="M18 15v6h2"></path>
  <path d="M13 15a2 2 0 0 1 2 2v2a2 2 0 1 1 -4 0v-2a2 2 0 0 1 2 -2z"></path>
  <path d="M14 20l1.5 1.5"></path>
</g>

<g id="db">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M12 6m-8 0a8 3 0 1 0 16 0a8 3 0 1 0 -16 0"></path>
  <path d="M4 6v6a8 3 0 0 0 16 0v-6"></path>
  <path d="M4 12v6a8 3 0 0 0 16 0v-6"></path>
</g>

<g id="email">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M3 7a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v10a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-10z"></path>
  <path d="M3 7l9 6l9 -6"></path>
</g>

<g id="cert">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M15 15m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"></path>
  <path d="M13 17.5v4.5l2 -1.5l2 1.5v-4.5"></path>
  <path d="M10 19h-5a2 2 0 0 1 -2 -2v-10c0 -1.1 .9 -2 2 -2h14a2 2 0 0 1 2 2v10a2 2 0 0 1 -1 1.73"></path>
  <path d="M6 9l12 0"></path>
  <path d="M6 12l3 0"></path>
  <path d="M6 15l2 0"></path>
</g>

<g id="keystore">
  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
  <path d="M16.555 3.843l3.602 3.602a2.877 2.877 0 0 1 0 4.069l-2.643 2.643a2.877 2.877 0 0 1 -4.069 0l-.301 -.301l-6.558 6.558a2 2 0 0 1 -1.239 .578l-.175 .008h-1.172a1 1 0 0 1 -.993 -.883l-.007 -.117v-1.172a2 2 0 0 1 .467 -1.284l.119 -.13l.414 -.414h2v-2h2v-2l2.144 -2.144l-.301 -.301a2.877 2.877 0 0 1 0 -4.069l2.643 -2.643a2.877 2.877 0 0 1 4.069 0z"></path>
  <path d="M15 9h.01"></path>
</g>
</defs>
</svg>
<header>
    <h1>"""
                     f'{path_top_dir.name}'
                     """</h1>
                 </header>
                 <main>
                 <div class="listing">
                     <table aria-describedby="summary">
                         <thead>
                         <tr>
                             <th></th>
                             <th>Name</th>
                             <th>Size</th>
                             <th class="hideable">
                                 Modified
                             </th>
                             <th class="hideable"></th>
                         </tr>
                         </thead>
                         <tbody>
                         <tr class="clickable">
                             <td></td>
                             <td><a href="..">
                                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-corner-left-up" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                                    <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                                    <path d="M18 18h-6a3 3 0 0 1 -3 -3v-10l-4 4m8 0l-4 -4"></path>
                                </svg>
                 <span class="goup">..</span></a></td>
                             <td>&mdash;</td>
                             <td class="hideable">&mdash;</td>
                             <td class="hideable"></td>
                         </tr>
                 """)

    # sort dirs first
    sorted_entries = sorted(path_top_dir.glob(glob_patt), key=lambda p: (not p.is_dir(), p.name))

    entry: Path
    for entry in sorted_entries:

        # - don't include index.html in the file listing
        # - skip .hidden dot files unless explicitly requested
        # - skip by regex if defined
        if (entry.name.lower() == opts.output_file.lower()) \
                or (not opts.include_hidden and entry.name.startswith('.')) \
                or (opts.exclude_regex and opts.exclude_regex.search(entry.name)):
            continue

        if entry.is_dir() and opts.recursive:
            process_dir(entry, opts)

        # From Python 3.6, os.access() accepts path-like objects
        if (not entry.is_symlink()) and not os.access(str(entry), os.R_OK):
            print(f"*** WARNING *** entry {entry.absolute()} is not readable! SKIPPING!")
            continue
        if opts.verbose:
            print(f'{entry.absolute()}')

        size_bytes = -1  # is a folder
        size_pretty = '&mdash;'
        last_modified = '-'
        last_modified_human_readable = '-'
        last_modified_iso = ''
        try:
            if entry.is_file():
                size_bytes = entry.stat().st_size
                size_pretty = pretty_size(size_bytes)

            if entry.is_dir() or entry.is_file():
                last_modified = datetime.datetime.fromtimestamp(entry.stat().st_mtime).replace(microsecond=0)
                last_modified_iso = last_modified.isoformat()
                last_modified_human_readable = last_modified.strftime("%c")

        except Exception as e:
            print('ERROR accessing file name:', e, entry)
            continue

        entry_path = str(entry.name)

        icon_xlink = None
        css_class_svg = ""

        if entry.is_dir() and not entry.is_symlink():
            icon_xlink = 'folder'
            css_class_svg = "folder_filled"

            if os.name not in ('nt',):
                # append trailing slash to dirs, unless it's windows
                entry_path = os.path.join(entry.name, '')

        elif entry.is_dir() and entry.is_symlink():
            icon_xlink = 'folder-symlink'

            print('dir-symlink', entry.absolute())

        elif entry.is_file() and entry.is_symlink():
            icon_xlink = 'symlink'

            print('file-symlink', entry.absolute())

        elif entry.is_file():

            if '.' in entry.name:
                icon_xlink = EXTENSION_TYPES.get(entry.suffix.lower())
            else:
                icon_xlink = EXTENSION_TYPES.get(entry.name)

        if icon_xlink is None:
            icon_xlink = 'generic'

        index_file.write(f"""
        <tr class="file">
            <td></td>
            <td>
                <a href="{quote(entry_path)}">
                
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><use xlink:href="#{icon_xlink}" class="{css_class_svg}"></use></svg>
                    <span class="name">{entry.name}</span>
                </a>
            </td>
            <td data-order="{size_bytes}">{size_pretty}</td>
            <td class="hideable"><time datetime="{last_modified_iso}">{last_modified_human_readable}</time></td>
            <td class="hideable"></td>
        </tr>
""")

    index_file.write("""
            </tbody>
        </table>
    </div>
</main>
</body>
</html>""")
    if index_file:
        index_file.close()


# bytes pretty-printing
UNITS_MAPPING = [
    (1024 ** 5, ' PB'),
    (1024 ** 4, ' TB'),
    (1024 ** 3, ' GB'),
    (1024 ** 2, ' MB'),
    (1024 ** 1, ' KB'),
    (1024 ** 0, (' byte', ' bytes')),
]


def pretty_size(bytes, units=UNITS_MAPPING):
    """Human-readable file sizes.

    ripped from https://pypi.python.org/pypi/hurry.filesize/
    """
    for factor, suffix in units:
        if bytes >= factor:
            break
    amount = int(bytes / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix


def type_regex(s):
    if not s:
        return None
    try:
        return re.compile(s)
    except re.error as e:
        raise argparse.ArgumentTypeError(f"Invalid regular expression: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='''DESCRIPTION:
    Generate directory index files (recursive is OFF by default).
    Start from current dir or from folder passed as first positional argument.
    Optionally filter by file types with --filter "*.py". ''')

    parser.add_argument('top_dir',
                        nargs='?',
                        action='store',
                        help='top folder from which to start generating indexes, '
                             'use current folder if not specified',
                        default=os.getcwd())

    parser.add_argument('--filter', '-f',
                        help='only include files matching glob',
                        required=False)

    parser.add_argument('--output-file', '-o',
                        metavar='filename',
                        default=DEFAULT_OUTPUT_FILE,
                        help=f'Custom output file, by default "{DEFAULT_OUTPUT_FILE}"')

    parser.add_argument('--recursive', '-r',
                        action='store_true',
                        help="recursively process nested dirs (FALSE by default)",
                        required=False)

    parser.add_argument('--include-hidden', '-i',
                        action='store_true',
                        help="include dot hidden files (FALSE by default)",
                        required=False)

    parser.add_argument('--exclude-regex', '-x',
                        type=type_regex,
                        help="exclude files matching regular expression",
                        required=False)

    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='WARNING: can take longer time with complex file tree structures on slow terminals -'
                             ' verbosely list every processed file',
                        required=False)

    config = parser.parse_args(sys.argv[1:])
    process_dir(config.top_dir, config)
