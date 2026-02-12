## 🚀 DeepSeek Desktop

![CI](https://img.shields.io/github/actions/workflow/status/notlousybook/DeepSeek-Desktop/ci.yml?style=flat&label=CI)
![Version](https://img.shields.io/github/v/release/notlousybook/DeepSeek-Desktop?style=flat&color=blue)
![Language](https://img.shields.io/github/languages/top/notlousybook/DeepSeek-Desktop?style=flat&color=yellow)
![License](https://img.shields.io/github/license/notlousybook/DeepSeek-Desktop?style=flat&color=green)

> Your ultimate desktop companion for DeepSeek Chat — now smoother, prettier, and packed with magic ✨

**⚠️ Note:** This project is still under active development. Expect more crazy features soon!
> Updated to version 0.1.70 added linux build support.

> Added Linux build support and AppImage

> Bugs or suggestions? Drop them in [issues](https://github.com/notlousybook/DeepSeek-Desktop/issues) 💀🔥

![DeepSeek Desktop Preview](assets/preview.png)

---

## 📖 Table of Contents

- [💾 Installation](#-installation)
- [✨ Features](#-features)
- [📸 Screenshots](#-screenshots)
- [🔧 Advanced Usage](#-advanced-usage)
- [🔮 Future Plans](#-future-plans)
- [👋 Connect with Me](#-connect-with-me)
- [🤘 Cool Contributors](#-cool-contributors)
- [🔧 Bots that help the project](#bots-that-help-the-project)
- [⚡ Attribution](#-attribution)

---

## 💾 Installation

### For Windows

1. Head to the [Releases page](https://github.com/notlousybook/DeepSeek-Desktop/releases)
2. Download `DeepSeekChat-windows.zip`
3. Extract the files
4. Run `DeepSeekChat.exe`
5. The app now features an **Integrated Auto-Updater**! When a new version is released, you'll see a notification directly in the app to update and restart seamlessly. 🚀

---

### For Linux

1. Head to the [Releases page](https://github.com/notlousybook/DeepSeek-Desktop/releases)
2. Download `DeepSeek_Desktop.AppImage`
3. Make it executable:
   ```bash
   chmod +x DeepSeek_Desktop.AppImage
   ```
4. Run `DeepSeek_Desktop.AppImage`

---

## ✨ Features

**DeepSeek Desktop** comes loaded with enhancements to make your chat experience 💯:

* 🎨 **Custom UI Elements**
  * Custom footer text
  * Forced **Inter font** throughout

* ⏰ **Dynamic Greetings**
  * Good Morning/Afternoon/Evening messages
  * **500+ unique greetings** with random display
  * Smooth fade transitions and typing animations

* ✨ **Animations**
  * Typing animation with sphere cursor
  * Self-healing UI via MutationObservers

* 🧹 **Clean Interface**
  * Removed cluttered UI elements
  * Persistent styling across navigation

* 🌙 **Dark Titlebar Support**
  * Matches your Windows system theme automatically
  * Manual override available

* 🔃 **Integrated Auto Updater**
  * **In-UI Notifications**: Sleek glassmorphic banner when a new version is available
  * **One-Click Update**: Restart and update directly from the app
  * **Manual Check**: Press **Ctrl+Shift+U** to trigger a check anytime
  * **Linux Build**: Auto-update is currently **not supported** on Linux. Updates are done by downloading a new AppImage.

* 🔄 **Real-time Sync & Navigation**
  * Frosted glass refresh button with auto-hide
  * URL path preserved on refresh
  * Smooth loading indicators & popups
  * Welcome tooltip for first-time guidance
  
* 📝 **Enhanced Markdown Rendering**
  * Full markdown support in messages
  * System theme detection for code blocks
  * JetBrains Mono for code readability
  * XSS protection via DOMPurify
  * Proper spacing & inline code handling

* 📸 **Developer & Utility Tools**
  * **Ctrl+Shift+S**: Instantly capture a screenshot of the window (Development mode only)
  * **Ctrl+Shift+U**: Manually trigger an update check (Works in both dev and production)
  * **Ctrl+Shift+L**: Open the logs viewer window (Works in both dev and production)
  * Screenshots are automatically saved to the `assets/` folder with timestamps
  * For the Linux build, it may or may not work depending on your distro

* 📊 **Comprehensive Logging System**
  * **Always Active**: Logs are recorded from the moment the app starts, even when the log viewer is closed
  * **Timestamped Entries**: Every log includes a precise timestamp for easy debugging
  * **Smart Management**: Automatically keeps the last 1000 log entries to manage memory usage
  * **Log Viewer Features**:
    - Dark theme CustomTkinter interface
    - Real-time log display with timestamps
    - Refresh, Copy All, Save to File, and Clear buttons
    - Scrollable text area for easy navigation
  * **Export Options**: Save logs to timestamped text files or copy to clipboard

---

## 📸 Screenshots

![DeepSeek Desktop Preview](assets/1.png)
![DeepSeek Desktop Preview](assets/2.png)
![DeepSeek Desktop Preview](assets/3.png)
![DeepSeek Desktop Preview](assets/4.png)



## 🔧 Advanced Usage

> Currently only functional on Windows

> Currently only functional on windows

```bash
# Force dark titlebar
DeepSeekChat.exe --dark-titlebar

# Force light titlebar
DeepSeekChat.exe --light-titlebar

# Run in release mode (disable debug tools)
DeepSeekChat.exe --release

# Take a screenshot (Development mode only)
# Press Ctrl + Shift + S

# Check for updates manually
# Press Ctrl + Shift + U
```

By default, the titlebar **matches your Desktop theme** automatically 🌙☀️

---

## 🔮 Future Plans

* [x] Dark titlebar ✅
* [ ] Custom themes
* [x] Keyboard shortcuts (Screenshot: Ctrl+Shift+S, Update: Ctrl+Shift+U) ✅
* [x] Cross-platform builds (Linux) ✅
* [ ] System tray integration

---

## 👋 Connect with Me

* [YouTube](https://www.youtube.com/channel/UCBNE8MNvq1XppUmpAs20m4w)
* [GitHub](https://github.com/notlousybook)

---

## 🤘 Cool Contributors

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
                <a href="https://github.com/notlousybook">
                    <img src="https://avatars.githubusercontent.com/u/197344995?v=4" width="100;" alt="notlousybook"/>
                    <br />
                    <sub><b>▷『 løµsʏ₿◌□₭ ▯↿ 』◀    (^◕.◕^)</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/dwip-the-dev">
                    <img src="https://avatars.githubusercontent.com/u/212593294?v=4" width="100;" alt="dwip-the-dev"/>
                    <br />
                    <sub><b>Dwip Biswas </b></sub>
                </a>
            </td>
		</tr>
	<tbody>
</table>
<!-- readme: collaborators,contributors -end -->

## 🔧Bots that help the project

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

## ⚡ Attribution

* Icons by [Icons8](https://icons8.com)
* Powered by [DeepSeek](https://deepseek.com)
