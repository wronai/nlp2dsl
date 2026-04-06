# Tauri voice chat wrapper

Desktop wrapper dla istniejącego voice chat backendu w `nlp-service`.

## Co robi

- Otwiera istniejący ekran `http://localhost:8002/chat`
- Korzysta z backendowego `navigator.mediaDevices.getUserMedia()` + `MediaRecorder`
- Nie duplikuje STT/TTS ani logiki WebSocket

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

## Build

```bash
npm run build
```

## Uwagi

- Jeśli backend działa na innym hoście lub porcie, zmień `build.devPath` w `src-tauri/tauri.conf.json` oraz `BACKEND_BASE` w `dist/app.js`.
- Ikona bundle jest zdefiniowana w `src-tauri/icons/icon.svg`.
