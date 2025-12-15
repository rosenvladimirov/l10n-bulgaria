# Welcome to Markdown Viewer

This is the **English version** of the documentation.

## Features

- ✅ Automatic language detection
- ✅ Fallback to English if translation not available
- ✅ Full Markdown support
- ✅ Code highlighting

## Example Code
python def hello(): print("Hello World!")

## How it works

The system detects your Odoo language setting and loads the appropriate file:
- `en_US` → loads `readme.md`
- `bg_BG` → loads `readme.bg.md`
- If localized file doesn't exist → fallback to `readme.md`
