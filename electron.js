"use strict";

const {
    app,
    BrowserWindow,
    ipcMain
} = require("electron");

const path = require("path");
const { spawn } = require("child_process");

let mainWindow = null;
let pythonProcess = null;
let quitting = false;

const PROJECT_ROOT = path.resolve(__dirname, "..");

const PYTHON = path.join(
    PROJECT_ROOT,
    ".venv",
    "bin",
    "python"
);


/* ==========================================================
   START PYTHON BACKEND
========================================================== */

function startPythonBackend() {

    if (pythonProcess) {
        console.log("[NOVA] Backend already running.");
        return;
    }

    console.log("[NOVA] Starting Python backend...");

    pythonProcess = spawn(
        PYTHON,
        [
            "-m",
            "api.server"
        ],
        {
            cwd: PROJECT_ROOT,
            stdio: "inherit"
        }
    );

    pythonProcess.on(
        "error",
        error => {

            console.error(
                "[NOVA] Python backend error:",
                error
            );

        }
    );

    pythonProcess.on(
        "exit",
        (code, signal) => {

            console.log(
                `[NOVA] Python exited: ${code} ${signal || ""}`
            );

            pythonProcess = null;

        }
    );

}


/* ==========================================================
   STOP PYTHON BACKEND
========================================================== */

function stopPythonBackend() {

    if (!pythonProcess) {
        return;
    }

    console.log(
        "[NOVA] Stopping Python backend..."
    );

    try {

        pythonProcess.kill("SIGTERM");

    } catch (error) {

        console.error(
            "[NOVA] Failed to stop backend:",
            error
        );

    }

    pythonProcess = null;

}


/* ==========================================================
   CREATE WINDOW
========================================================== */

function createWindow() {

    mainWindow =
        new BrowserWindow({

            width: 1400,

            height: 900,

            minWidth: 1100,

            minHeight: 700,

            backgroundColor: "#05070B",

            title: "NOVA",

            show: false,

            webPreferences: {

                preload: path.join(
                    __dirname,
                    "preload.js"
                ),

                contextIsolation: true,

                nodeIntegration: false

            }

        });


    mainWindow.loadFile(
        path.join(
            __dirname,
            "index.html"
        )
    );


    mainWindow.once(
        "ready-to-show",
        () => {

            if (mainWindow) {
                mainWindow.show();
            }

        }
    );


    /* ======================================================
       WINDOW CLOSED
    ====================================================== */

    mainWindow.on(
        "closed",
        () => {

            mainWindow = null;

            if (!quitting) {

                console.log(
                    "[NOVA] Window closed. Shutting down..."
                );

                quitting = true;

                stopPythonBackend();

                app.quit();

            }

        }
    );

}


/* ==========================================================
   EXIT FROM FRONTEND
========================================================== */

ipcMain.on(
    "nova-quit",
    () => {

        console.log(
            "[NOVA] Exit requested."
        );

        quitting = true;

        stopPythonBackend();

        if (mainWindow) {

            mainWindow.destroy();

            mainWindow = null;

        }

        app.quit();

    }
);


/* ==========================================================
   MINIMIZE
========================================================== */

ipcMain.on(
    "nova-minimize",
    () => {

        if (mainWindow) {
            mainWindow.minimize();
        }

    }
);


/* ==========================================================
   MAXIMIZE
========================================================== */

ipcMain.on(
    "nova-maximize",
    () => {

        if (!mainWindow)
            return;

        if (
            mainWindow.isMaximized()
        ) {

            mainWindow.unmaximize();

        } else {

            mainWindow.maximize();

        }

    }
);


/* ==========================================================
   APP READY
========================================================== */

app.whenReady().then(
    () => {

        console.log(
            "[NOVA] Electron ready."
        );

        startPythonBackend();

        setTimeout(
            () => {

                createWindow();

            },
            1500
        );


        app.on(
            "activate",
            () => {

                if (
                    BrowserWindow
                        .getAllWindows()
                        .length === 0
                ) {

                    createWindow();

                }

            }
        );

    }
);


/* ==========================================================
   MACOS
========================================================== */

app.on(
    "window-all-closed",
    () => {

        if (
            process.platform !== "darwin"
        ) {

            app.quit();

        }

    }
);


/* ==========================================================
   FINAL SHUTDOWN
========================================================== */

app.on(
    "before-quit",
    () => {

        if (quitting) {

            stopPythonBackend();

        }

    }
);


/* ==========================================================
   EXTRA SAFETY
========================================================== */

process.on(
    "exit",
    () => {

        stopPythonBackend();

    }
);