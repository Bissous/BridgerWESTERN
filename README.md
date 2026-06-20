# RGTF Macro

A fishing macro for *Bridger: WESTERN* on Roblox. It watches the center of the
screen for the R, G, T and F prompts and presses the matching key automatically.

## Demo

[![Watch the demo](https://img.youtube.com/vi/DerJJCNpmmw/maxresdefault.jpg)](https://youtu.be/DerJJCNpmmw?si=bDXqY8ct1oHFolwX)

[Watch the demo on YouTube](https://youtu.be/DerJJCNpmmw?si=bDXqY8ct1oHFolwX)

## Requirements

- Windows 10 or 11
- Screen resolution of 1920x1080 (the scan area is calibrated for it)
- [Visual C++ Redistributable 2015-2022](https://aka.ms/vs/17/release/vc_redist.x64.exe), if the app fails to start

## Installation

Download `RGTFMacro.exe` from the [Releases page](https://github.com/Bissous/BridgerWESTERN/releases).
It's a portable executable, so there's nothing to install.

## Usage

1. Run the executable as administrator (required to simulate key presses).
2. Press Run, or F6, to start detection.
3. Press Stop, or F6, to stop.

The window stays on top so you can toggle it without leaving the game.

## Run from source

```
pip install -r requirements.txt
python macro.py
```

## Build the executable

```
pip install pyinstaller
pyinstaller RGTFMacro.spec
```

The result lands in `dist/`.

## Disclaimer

For educational purposes. Using macros may breach the Roblox Terms of Service;
use it at your own risk.

## License

[MIT](LICENSE)
