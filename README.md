<!--
# SPDX-FileCopyrightText: Copyright 2025 Eden Emulator Project
# SPDX-License-Identifier: GPL-3.0-or-later

# SPDX-FileCopyrightText: 2018 yuzu Emulator Project
# SPDX-License-Identifier: GPL-2.0-or-later
-->

<p align="center">
  <img src="dist/branding/dist/branding/Chata_icon_with_logo.png.PNG" alt="Chata" width="600">
</p>

# Chata

Chata is an experimental, open-source Nintendo Switch and Switch 2 emulator written in C++. It is a fork of Lichii, which builds on Eglantine, Eden, yuzu and Sudachi. Chata preserves their contributions and adds packaging and platform work, with a focus on Linux x86-64 and the Steam Deck.

This is an independent fork, not an official release of Lichii or of any of those upstream projects. Chata is not affiliated with Nintendo.
This is an independent fork, not an official release of those upstream projects. Lichii is not affiliated with Nintendo.

## Downloads and setup

Published builds belong on this fork's releases page.

	•	Linux (x86-64): builds are distributed as an AppImage. Make it executable and run it: chmod +x <file>.AppImage && ./<file>.AppImage. If it fails to start because of FUSE, run it with --appimage-extract-and-run.
	•	Windows: extract the entire build archive and run the main executable (currently named lichii.exe).

Only use games and system files you have legally obtained. Games, keys and firmware are not included.

### Existing saves and settings

The rebrand intentionally retains the existing Eden/Eglantine data directories and configuration keys. It does not move or delete saves, settings or shader caches. Back up your saves before testing experimental builds

## Compatibility and issue reports

Compatibility and performance vary by game, hardware and driver. Rendering errors, stutters and crashes remain possible. Passing automated tests does not establish that a game renders correctly, and this project makes no universal frame-rate guarantee.

Compatibility and performance vary by game, hardware and driver. Rendering errors, stutters and crashes remain possible. Passing automated tests does not establish that a game renders correctly, and this project makes no universal frame-rate guarantee.

When reporting an issue, include:

	•	The exact build, game version, CPU, GPU and driver version.
	•	Relevant settings and steps to reproduce the problem.
	•	A screenshot and the log from the affected session, after checking it for personal information.

Do not upload game files, keys, firmware or private account information.

## Building and contributing

See the build guide, user documentation and coding guidelines. Some inherited documentation and internal build target names still use upstream names. The GUI build target remains yuzu; its output is currently named lichii.exe on Windows and lichii on other desktop platforms.

Keep changes focused and distinguish code-level checks from actual gameplay testing.

## Artwork
The Chata logo is original artwork for this project.

## Credits and license

Chata inherits the work of the Lichii, Eglantine, Eden, yuzu and Sudachi projects and their contributors, including Lichii's maintainer zortos293 and Eglantine's original developer Camille LaVey. Original copyright notices and third-party licenses are retained.

Chata is distributed under the same license terms as the code it is derived from, GPL-3.0-or-later. Files have been modified from the upstream versions; see the git history for details.

See LICENSE.txt and the source files for applicable license terms.
