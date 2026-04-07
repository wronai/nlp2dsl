#!/usr/bin/env node

const http = require("node:http");
const fs = require("node:fs/promises");
const path = require("node:path");

const HOST = process.env.TAURI_LAUNCHER_HOST || "127.0.0.1";
const PORT = Number.parseInt(process.env.TAURI_LAUNCHER_PORT || "1420", 10);
const ROOT_DIR = path.resolve(__dirname, "..", "dist");

const MIME_TYPES = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".js", "application/javascript; charset=utf-8"],
  [".mjs", "application/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".ico", "image/x-icon"],
  [".txt", "text/plain; charset=utf-8"],
  [".map", "application/json; charset=utf-8"],
]);

function contentType(filePath) {
  return MIME_TYPES.get(path.extname(filePath).toLowerCase()) || "application/octet-stream";
}

function isInsideRoot(candidatePath) {
  const relativePath = path.relative(ROOT_DIR, candidatePath);
  return relativePath === "" || (!relativePath.startsWith("..") && !path.isAbsolute(relativePath));
}

async function resolveRequestPath(requestPath) {
  const safePath = decodeURIComponent(requestPath || "/").split("?")[0].split("#")[0];

  if (safePath === "/" || safePath === "") {
    return path.join(ROOT_DIR, "index.html");
  }

  const candidate = path.resolve(ROOT_DIR, `.${safePath}`);
  if (!isInsideRoot(candidate)) {
    return null;
  }

  try {
    const stat = await fs.stat(candidate);
    if (stat.isDirectory()) {
      return path.join(candidate, "index.html");
    }
    return candidate;
  } catch (error) {
    if (path.extname(candidate)) {
      return null;
    }
    return path.join(ROOT_DIR, "index.html");
  }
}

async function sendFile(res, filePath) {
  const fileContents = await fs.readFile(filePath);
  res.writeHead(200, {
    "Cache-Control": "no-store",
    "Content-Type": contentType(filePath),
  });
  res.end(fileContents);
}

async function handleRequest(req, res) {
  if (!req.url) {
    res.writeHead(400, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Bad request");
    return;
  }

  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, {
      Allow: "GET, HEAD",
      "Content-Type": "text/plain; charset=utf-8",
    });
    res.end("Method not allowed");
    return;
  }

  const pathname = new URL(req.url, `http://${HOST}:${PORT}`).pathname;
  const targetPath = await resolveRequestPath(pathname);

  if (!targetPath) {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Not found");
    return;
  }

  if (req.method === "HEAD") {
    res.writeHead(200, {
      "Cache-Control": "no-store",
      "Content-Type": contentType(targetPath),
    });
    res.end();
    return;
  }

  await sendFile(res, targetPath);
}

function startServer() {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      handleRequest(req, res).catch((error) => {
        console.error("[launcher] Unexpected error while serving request:", error);
        if (!res.headersSent) {
          res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
        }
        res.end("Internal server error");
      });
    });

    server.once("error", reject);
    server.listen(PORT, HOST, () => {
      console.log(`[launcher] Serving ${ROOT_DIR} at http://${HOST}:${PORT}`);
      resolve(server);
    });
  });
}

module.exports = {
  HOST,
  PORT,
  ROOT_DIR,
  startServer,
};

if (require.main === module) {
  startServer().catch((error) => {
    console.error("[launcher] Failed to start server:", error);
    process.exit(1);
  });
}
