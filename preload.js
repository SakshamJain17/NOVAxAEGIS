"use strict";

const {
    contextBridge,
    ipcRenderer
} = require("electron");


/* ==========================================================
   NOVA BACKEND
========================================================== */

const NOVA_SERVER =
    "ws://127.0.0.1:8765/ws";

const NOVA_HEALTH =
    "http://127.0.0.1:8765/health";


let socket = null;


/* ==========================================================
   WEBSOCKET CONNECTION
========================================================== */

function connect() {

    /*
     * Reuse existing connection
     */

    if (
        socket &&
        (
            socket.readyState === WebSocket.OPEN ||
            socket.readyState === WebSocket.CONNECTING
        )
    ) {

        return socket;

    }


    console.log(
        "[NOVA PRELOAD] Connecting to NOVA CORE..."
    );


    socket =
        new WebSocket(
            NOVA_SERVER
        );


    socket.addEventListener(
        "open",
        () => {

            console.log(
                "[NOVA PRELOAD] WebSocket connected."
            );

        }
    );


    socket.addEventListener(
        "close",
        () => {

            console.log(
                "[NOVA PRELOAD] WebSocket closed."
            );

        }
    );


    socket.addEventListener(
        "error",
        error => {

            console.error(
                "[NOVA PRELOAD] WebSocket error:",
                error
            );

        }
    );


    return socket;

}


/* ==========================================================
   SEND MESSAGE
========================================================== */

function send(
    message
) {

    if (
        !socket ||
        socket.readyState !== WebSocket.OPEN
    ) {

        throw new Error(
            "NOVA backend is not connected."
        );

    }


    socket.send(
        JSON.stringify(
            message
        )
    );

}


/* ==========================================================
   HEALTH CHECK
========================================================== */

async function health() {

    const response =
        await fetch(
            NOVA_HEALTH
        );


    if (!response.ok) {

        throw new Error(
            `NOVA health check failed: ${response.status}`
        );

    }


    return await response.json();

}


/* ==========================================================
   CONNECTION STATUS
========================================================== */

function isConnected() {

    return (
        socket &&
        socket.readyState === WebSocket.OPEN
    );

}


/* ==========================================================
   QUIT NOVA
========================================================== */

function quit() {

    console.log(
        "[NOVA PRELOAD] Shutdown requested."
    );


    /*
     * Close WebSocket first.
     */

    if (
        socket &&
        socket.readyState === WebSocket.OPEN
    ) {

        try {

            socket.close();

        } catch (error) {

            console.error(
                "[NOVA PRELOAD] Socket close error:",
                error
            );

        }

    }


    socket = null;


    /*
     * Tell Electron main process
     * to terminate NOVA completely.
     */

    ipcRenderer.send(
        "nova-quit"
    );

}


/* ==========================================================
   MINIMIZE
========================================================== */

function minimize() {

    ipcRenderer.send(
        "nova-minimize"
    );

}


/* ==========================================================
   MAXIMIZE
========================================================== */

function maximize() {

    ipcRenderer.send(
        "nova-maximize"
    );

}


/* ==========================================================
   EXPOSE NOVA API
========================================================== */

contextBridge.exposeInMainWorld(
    "nova",
    {

        /* Backend */

        connect,

        send,

        health,

        isConnected,


        /* Window */

        quit,

        minimize,

        maximize

    }
);


console.log(
    "[NOVA PRELOAD] NOVA bridge initialized."
);