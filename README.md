# Mozaik Browser Patcher

Patch `Mozaik.exe` and `MozaikData.dll` entirely in your browser. Files never leave your machine.

## Use the site

1. Upload `Mozaik.exe` and `MozaikData.dll` (from `C:\Mozaik\System\`).
2. Click **Patch files**.
3. Download the patched files and replace them (back up originals first):
   - `C:\Mozaik\Mozaik.exe`
   - `C:\Mozaik\System\MozaikData.dll`

## Develop locally

```bash
dotnet publish -c Release
python serve.py
```

Open http://localhost:8080

## Publish to GitHub Pages

This folder is meant to be the **root of its own GitHub repo**.

```bash
cd mozaik-patcher   # or copy this folder elsewhere first
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOU/REPO_NAME.git
git branch -M main
git push -u origin main
```

Then in GitHub: **Settings → Pages → Source → GitHub Actions**.

After the workflow runs:

- Project repo: `https://YOU.github.io/REPO_NAME/`
- User site repo (`YOU.github.io`): `https://YOU.github.io/`

## Build from source

Requires [.NET 8 SDK](https://dotnet.microsoft.com/download).

```bash
dotnet new install Microsoft.NET.Runtime.WebAssembly.Templates
dotnet publish -c Release
```

Output: `bin/Release/net8.0/publish/wwwroot/`
