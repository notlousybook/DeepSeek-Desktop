# DeepSeek Desktop

[![CI](https://img.shields.io/github/actions/workflow/status/LousyBook94/DeepSeek-Desktop/ci.yml?style=flat&label=CI)](https://github.com/LousyBook94/DeepSeek-Desktop/actions)
[![Version](https://img.shields.io/github/v/release/LousyBook94/DeepSeek-Desktop?style=flat&color=blue)](https://github.com/LousyBook94/DeepSeek-Desktop/releases)
[![Language](https://img.shields.io/github/languages/top/LousyBook94/DeepSeek-Desktop?style=flat&color=yellow)](https://github.com/LousyBook94/DeepSeek-Desktop)
[![License](https://img.shields.io/github/license/LousyBook94/DeepSeek-Desktop?style=flat&color=green)](LICENSE)

A cozy desktop wrapper for DeepSeek Chat — smoother, prettier, and nice to use :3

> **Heads up!** This project is actively being worked on, so expect new things to land regularly.
> 
> If you're on a version older than 0.1.69, please update — the old updater was horrendously buggy (no GUI, pretty broken). Much better now!
>
> Found a bug or have an idea? [Open an issue](https://github.com/notlousybook/DeepSeek-Desktop/issues) — I'd love to hear from you.

![DeepSeek Desktop Preview](assets/preview.png)

---

## What's Inside

- [Installation](#installation)
- [Features](#features)
- [Screenshots](#screenshots)
- [Tips & Tricks](#tips--tricks)
- [What's Coming](#whats-coming)
- [Contributors](#contributors)
- [Bots](#bots)
- [Credits](#credits)

---

## Installation

1. Grab the latest release from the [Releases page](https://github.com/notlousybook/DeepSeek-Desktop/releases)
2. Download `DeepSeekChat-windows.zip`
3. Extract it somewhere nice
4. Run `DeepSeekChat.exe`

The app will keep itself updated automatically — you'll get a friendly notification when there's something new :3

---

## Features

**The Nice Stuff**
- Clean, calm interface with custom footer text
- Lovely Inter font throughout
- Dynamic greetings that change based on time of day (500+ variations, so you won't see the same one too often)
- Smooth fade transitions and typing animations
- Clutter-free design that stays consistent as you navigate

**Fits Your System**
- Titlebar matches your Windows theme automatically (dark or light)
- Want to force it? You can do that too

**Stays Up to Date**
- Glassmorphic update notifications when new versions drop
- One-click to update and restart
- Or press `Ctrl+Shift+U` to check manually anytime

**For the Curious**
- `Ctrl+Shift+S` — snap a screenshot (dev mode only, saves to `assets/`)
- `Ctrl+Shift+L` — peek at the logs
- `Ctrl+Shift+U` — check for updates

**Reads & Writes Well**
- Full markdown support in chats
- Code blocks that respect your system theme
- JetBrains Mono for code (easy on the eyes)
- XSS protection built in

**Logging That Actually Helps**
- Logs everything from startup, even when the viewer is closed
- Keeps the last 1000 entries so memory stays happy
- Dark-themed viewer with timestamps, search, and export options

---

## Screenshots

![Main Interface](assets/1.png)
![Chat View](assets/2.png)
![Settings](assets/3.png)
![Dark Mode](assets/4.png)

---

## Tips & Tricks

```bash
# Prefer dark mode?
DeepSeekChat.exe --dark-titlebar

# Prefer light mode?
DeepSeekChat.exe --light-titlebar

# Running it for real (disables debug shortcuts)
DeepSeekChat.exe --release
```

By default, it'll just follow your Windows theme.

---

## What's Coming

- [x] Dark titlebar support
- [x] Keyboard shortcuts
- [ ] Custom themes (pick your own colors!)
- [ ] macOS and Linux builds
- [ ] System tray integration

---

## Contributors

Made with care by these lovely people:

<!-- readme: collaborators,contributors -start -->
<table>
	<tbody>
		<tr>
            <td align="center">
                <a href="https://github.com/vanja-san">
                    <img src="https://avatars.githubusercontent.com/u/7201687?v=4" width="100;" alt="vanja-san"/>
                    <br />
                    <sub><b>Ioann</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/ang-or-five">
                    <img src="https://avatars.githubusercontent.com/u/99081841?v=4" width="100;" alt="ang-or-five"/>
                    <br />
                    <sub><b>ang</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/notlousybook">
                    <img src="https://avatars.githubusercontent.com/u/197344995?v=4" width="100;" alt="notlousybook"/>
                    <br />
                    <sub><b>▷『 løµsʏ₿◌□₭ ▯↿ 』◀ (^◕.◕^)</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/dwip-the-dev">
                    <img src="https://avatars.githubusercontent.com/u/212593294?v=4" width="100;" alt="dwip-the-dev"/>
                    <br />
                    <sub><b>Dwip Biswas</b></sub>
                </a>
            </td>
		</tr>
	<tbody>
</table>
<!-- readme: collaborators,contributors -end -->

---

## Bots

These automated helpers keep things running smoothly:

<!-- readme: bots -start -->
<table>
	<tbody>
		<tr>
            <td align="center">
                <a href="https://github.com/mentatbot[bot]">
                    <img src="https://avatars.githubusercontent.com/in/837875?v=4" width="100;" alt="mentatbot[bot]"/>
                    <br />
                    <sub><b>mentatbot[bot]</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/github-actions[bot]">
                    <img src="https://avatars.githubusercontent.com/in/15368?v=4" width="100;" alt="github-actions[bot]"/>
                    <br />
                    <sub><b>github-actions[bot]</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/google-labs-jules[bot]">
                    <img src="https://avatars.githubusercontent.com/in/842251?v=4" width="100;" alt="google-labs-jules[bot]"/>
                    <br />
                    <sub><b>google-labs-jules[bot]</b></sub>
                </a>
            </td>
		</tr>
	<tbody>
</table>
<!-- readme: bots -end -->

---

## Credits

- Icons by [Icons8](https://icons8.com)
- Built on top of [DeepSeek](https://deepseek.com)
