#!/usr/bin/env node

const { spawn } = require("node:child_process");
const { startServer } = require("./serve-dist");

async function main() {
  const server = await startServer();
  const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";

  const child = spawn(npmCommand, ["exec", "--", "tauri", "dev"], {
    env: process.env,
    stdio: "inherit",
  });

  let shuttingDown = false;

  const shutdown = async (code = 0) => {
    if (shuttingDown) {
      return;
    }

    shuttingDown = true;

    if (child.exitCode === null && child.signalCode === null) {
      child.kill("SIGTERM");
    }

    await new Promise((resolve) => {
      server.close(() => resolve());
    });

    process.exit(code ?? 0);
  };

  child.once("error", async (error) => {
    console.error("[launcher] Failed to start Tauri dev:", error);
    await shutdown(1);
  });

  child.once("exit", async (code, signal) => {
    const exitCode = signal === "SIGINT" ? 130 : signal === "SIGTERM" ? 143 : code ?? 0;
    await shutdown(exitCode);
  });

  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.once(signal, async () => {
      const exitCode = signal === "SIGINT" ? 130 : 143;
      await shutdown(exitCode);
    });
  }
}

main().catch((error) => {
  console.error("[launcher] Fatal error:", error);
  process.exit(1);
});
