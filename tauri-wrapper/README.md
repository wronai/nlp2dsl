# Tauri voice chat wrapper

Desktop wrapper dla istniejącego voice chat backendu w `nlp-service`.

## Co robi

- Otwiera istniejący ekran `http://127.0.0.1:8002/chat`
- Korzysta z backendowego `navigator.mediaDevices.getUserMedia()` + `MediaRecorder`
- Nie duplikuje STT/TTS ani logiki WebSocket

W trybie dev `npm run dev` uruchamia lokalny launcher na `http://127.0.0.1:1420`, który sprawdza backend i potem przełącza do czatu.

Jeśli nie masz wymaganych bibliotek WebKitGTK/GTK dla Tauri, użyj browserowego fallbacku:
`npm run desktop` albo `bash ./desktop.sh`. Otwiera on ten sam `/chat` w Chrome/Chromium `--app` mode.

### Linux prerequisites for Tauri dev

Na Linuxie Tauri v1 wymaga systemowych bibliotek WebKitGTK/GTK. Jeśli `npm run dev` kończy się błędem z brakującymi `libsoup-2.4` albo `javascriptcoregtk-4.0`, doinstaluj:

```bash
sudo apt install build-essential curl wget file libssl-dev libgtk-3-dev \
  libwebkit2gtk-4.0-dev libsoup2.4-dev libjavascriptcoregtk-4.0-dev \
  libayatana-appindicator3-dev librsvg2-dev
```

Jeśli używasz innej dystrybucji, zainstaluj odpowiednie odpowiedniki pakietów deweloperskich WebKitGTK/GTK.

## Uruchomienie

1. Uruchom backend z repo głównego:
   ```bash
   docker compose up --build
   ```

2. Zainstaluj zależności wrappera:
   ```bash
   npm install
   ```

3. Uruchom aplikację desktopową:
   ```bash
   npm run dev
   ```

   Jeśli Tauri nie startuje na Twoim systemie, użyj zamiast tego:
   ```bash
   npm run desktop
   ```

Launcher sprawdza backend pod `http://127.0.0.1:8002` i po health checku przechodzi do `http://127.0.0.1:8002/chat`.

## Build

```bash
npm run build
```

## Uwagi

- Jeśli backend działa na innym hoście lub porcie, zmień `BACKEND_BASE` w `dist/app.js` i odpowiednio dopasuj CSP w `src-tauri/tauri.conf.json`.
- Ikona bundle jest zdefiniowana w `src-tauri/icons/icon.svg`.
