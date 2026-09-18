/* ==========================================================
   NOVA 3D NEURAL CORE
   Advanced Electron Frontend
========================================================== */

"use strict";


/* ==========================================================
   GLOBAL STATE
========================================================== */

const NOVA = {

    state: "idle",

    speaking: false,

    listening: false,

    thinking: false,

    messages: 0,

    audioLevel: 0,

    targetAudioLevel: 0,

    connected: false

};


/* ==========================================================
   DOM
========================================================== */

const orbContainer =
    document.getElementById("orb-container");

const orbState =
    document.getElementById("orb-state");

const coreStatus =
    document.getElementById("core-status");

const voiceStatus =
    document.getElementById("voice-status");

const voiceWave =
    document.getElementById("voice-wave");

const commandInput =
    document.getElementById("command-input");

const sendButton =
    document.getElementById("send-button");

const micButton =
    document.getElementById("mic-button");

const stopButton =
    document.getElementById("stop-button");

const exitButton =
    document.getElementById("exit-button");

const conversation =
    document.getElementById("conversation");

const messageCount =
    document.getElementById("message-count");

const activity =
    document.getElementById("activity");

const systemTime =
    document.getElementById("system-time");

const minimizeButton =
    document.getElementById("minimize-button");

const maximizeButton =
    document.getElementById("maximize-button");

const sidebar =
    document.getElementById("sidebar");

const sidebarToggle =
    document.getElementById("sidebar-toggle");

const mobileSidebarButton =
    document.getElementById("mobile-sidebar-button");

const mobileBackdrop =
    document.getElementById("mobile-backdrop");

const newChatButton =
    document.getElementById("new-chat-button");

const chatHistory =
    document.getElementById("chat-history");

const chatSearch =
    document.getElementById("chat-search");

const welcomeScreen =
    document.getElementById("welcome-screen");

const CHAT_STORAGE_KEY =
    "nova-chat-history-v1";

let chatSessions = [];

let activeChatId = null;


/* ==========================================================
   THREE.JS VARIABLES
========================================================== */

let scene = null;

let camera = null;

let renderer = null;

let core = null;

let coreMaterial = null;

let particles = null;

let particleGeometry = null;

let particleMaterial = null;

let energyRing = null;

let energyRing2 = null;

let energyRing3 = null;

let outerShell = null;

let animationTime = 0;


/* ==========================================================
   WEBSOCKET
========================================================== */

let novaSocket = null;

let reconnectTimer = null;

let manuallyClosed = false;


/* ==========================================================
   SAFE DOM HELPERS
========================================================== */

function safeText(
    element,
    value
) {

    if (element) {

        element.textContent =
            value;

    }

}


/* ==========================================================
   THREE.JS INITIALIZATION
========================================================== */

function initializeOrb() {

    if (!orbContainer) {

        console.error(
            "[NOVA] Orb container not found."
        );

        return;

    }


    if (
        typeof THREE ===
        "undefined"
    ) {

        console.error(
            "[NOVA] Three.js unavailable."
        );

        return;

    }


    scene =
        new THREE.Scene();


    camera =
        new THREE.PerspectiveCamera(
            45,
            1,
            0.1,
            100
        );


    camera.position.z =
        6;


    renderer =
        new THREE.WebGLRenderer({

            antialias: true,

            alpha: true

        });


    renderer.setPixelRatio(
        Math.min(
            window.devicePixelRatio || 1,
            2
        )
    );


    renderer.setSize(
        Math.max(
            orbContainer.clientWidth,
            1
        ),
        Math.max(
            orbContainer.clientHeight,
            1
        )
    );


    if (
        "outputColorSpace"
        in renderer
    ) {

        renderer.outputColorSpace =
            THREE.SRGBColorSpace;

    }


    orbContainer.appendChild(
        renderer.domElement
    );


    /* ------------------------------------------------------
       LIGHTING
    ------------------------------------------------------ */

    const ambient =
        new THREE.AmbientLight(
            0x0a2233,
            2
        );


    scene.add(
        ambient
    );


    const point =
        new THREE.PointLight(
            0x00eaff,
            15,
            20
        );


    point.position.set(
        0,
        0,
        3
    );


    scene.add(
        point
    );


    createCore();

    createParticles();

    createEnergyRings();

    createOuterShell();


    window.addEventListener(
        "resize",
        resizeOrb
    );


    animateOrb();

}


/* ==========================================================
   CORE
========================================================== */

function createCore() {

    const geometry =
        new THREE.IcosahedronGeometry(
            1.15,
            5
        );


    coreMaterial =
        new THREE.MeshBasicMaterial({

            color: 0x00eaff,

            wireframe: true,

            transparent: true,

            opacity: 0.8

        });


    core =
        new THREE.Mesh(
            geometry,
            coreMaterial
        );


    scene.add(
        core
    );


    const innerGeometry =
        new THREE.SphereGeometry(
            0.83,
            64,
            64
        );


    const innerMaterial =
        new THREE.MeshBasicMaterial({

            color: 0x006eff,

            transparent: true,

            opacity: 0.13

        });


    const inner =
        new THREE.Mesh(
            innerGeometry,
            innerMaterial
        );


    core.add(
        inner
    );

}


/* ==========================================================
   PARTICLES
========================================================== */

function createParticles() {

    const count = 7000;


    particleGeometry =
        new THREE.BufferGeometry();


    const positions =
        new Float32Array(
            count * 3
        );


    const sizes =
        new Float32Array(
            count
        );


    for (
        let i = 0;
        i < count;
        i++
    ) {

        const radius =
            1.45 +
            Math.random() * 1.7;


        const theta =
            Math.random() *
            Math.PI *
            2;


        const phi =
            Math.acos(
                2 *
                Math.random() -
                1
            );


        positions[i * 3] =
            radius *
            Math.sin(phi) *
            Math.cos(theta);


        positions[i * 3 + 1] =
            radius *
            Math.sin(phi) *
            Math.sin(theta);


        positions[i * 3 + 2] =
            radius *
            Math.cos(phi);


        sizes[i] =
            Math.random() *
            2 +
            0.5;

    }


    particleGeometry.setAttribute(
        "position",
        new THREE.BufferAttribute(
            positions,
            3
        )
    );


    particleGeometry.setAttribute(
        "size",
        new THREE.BufferAttribute(
            sizes,
            1
        )
    );


    particleMaterial =
        new THREE.PointsMaterial({

            color: 0x00dfff,

            size: 0.018,

            transparent: true,

            opacity: 0.8,

            blending:
                THREE.AdditiveBlending,

            depthWrite: false

        });


    particles =
        new THREE.Points(
            particleGeometry,
            particleMaterial
        );


    scene.add(
        particles
    );

}


/* ==========================================================
   ENERGY RINGS
========================================================== */

function createEnergyRings() {

    const geometry =
        new THREE.TorusGeometry(
            1.55,
            0.008,
            16,
            180
        );


    const material =
        new THREE.MeshBasicMaterial({

            color: 0x00eaff,

            transparent: true,

            opacity: 0.65

        });


    energyRing =
        new THREE.Mesh(
            geometry,
            material
        );


    energyRing.rotation.x =
        Math.PI / 2.2;


    scene.add(
        energyRing
    );


    energyRing2 =
        new THREE.Mesh(
            geometry.clone(),
            material.clone()
        );


    energyRing2.material.color
        .setHex(0x168cff);


    energyRing2.rotation.y =
        Math.PI / 2.7;


    scene.add(
        energyRing2
    );


    energyRing3 =
        new THREE.Mesh(
            geometry.clone(),
            material.clone()
        );


    energyRing3.material.color
        .setHex(0x5ddcff);


    energyRing3.rotation.x =
        Math.PI / 3;


    energyRing3.rotation.z =
        Math.PI / 5;


    scene.add(
        energyRing3
    );

}


/* ==========================================================
   OUTER SHELL
========================================================== */

function createOuterShell() {

    const geometry =
        new THREE.SphereGeometry(
            1.55,
            48,
            48
        );


    const material =
        new THREE.MeshBasicMaterial({

            color: 0x00dfff,

            wireframe: true,

            transparent: true,

            opacity: 0.08

        });


    outerShell =
        new THREE.Mesh(
            geometry,
            material
        );


    scene.add(
        outerShell
    );

}


/* ==========================================================
   STATE SPEED
========================================================== */

function getStateMultiplier() {

    switch (
        NOVA.state
    ) {

        case "listening":
            return 2.5;

        case "thinking":
            return 3.4;

        case "speaking":
            return 2.8;

        case "error":
            return 0.35;

        case "paused":
            return 0.15;

        default:
            return 1;

    }

}


/* ==========================================================
   ORB ANIMATION
========================================================== */

function animateOrb() {

    requestAnimationFrame(
        animateOrb
    );


    if (
        !renderer ||
        !scene ||
        !camera
    ) {

        return;

    }


    animationTime +=
        0.01;


    const multiplier =
        getStateMultiplier();


    /* ------------------------------------------------------
       CORE
    ------------------------------------------------------ */

    if (core) {

        core.rotation.x +=
            0.0015 *
            multiplier;


        core.rotation.y +=
            0.003 *
            multiplier;


        core.rotation.z +=
            0.001 *
            multiplier;

    }


    /* ------------------------------------------------------
       PARTICLES
    ------------------------------------------------------ */

    if (particles) {

        particles.rotation.y +=
            0.0008 *
            multiplier;


        particles.rotation.x =
            Math.sin(
                animationTime * 0.2
            ) * 0.08;

    }


    /* ------------------------------------------------------
       RINGS
    ------------------------------------------------------ */

    if (energyRing) {

        energyRing.rotation.z +=
            0.004 *
            multiplier;

        energyRing.rotation.y +=
            0.001;

    }


    if (energyRing2) {

        energyRing2.rotation.x -=
            0.003 *
            multiplier;

        energyRing2.rotation.z +=
            0.002;

    }


    if (energyRing3) {

        energyRing3.rotation.y +=
            0.002 *
            multiplier;

        energyRing3.rotation.z -=
            0.003;

    }


    /* ------------------------------------------------------
       PULSE
    ------------------------------------------------------ */

    const pulse =
        1 +
        Math.sin(
            animationTime * 2.4
        ) * 0.025;


    let statePulse = 0;


    switch (
        NOVA.state
    ) {

        case "listening":

            statePulse =
                0.14 +
                Math.sin(
                    animationTime * 9
                ) * 0.10;

            break;


        case "thinking":

            statePulse =
                0.07 +
                Math.sin(
                    animationTime * 15
                ) * 0.045;

            break;


        case "speaking":

            statePulse =
                0.12 +
                Math.sin(
                    animationTime * 7
                ) * 0.08;

            break;


        case "error":

            statePulse =
                Math.sin(
                    animationTime * 18
                ) * 0.025;

            break;


        case "paused":

            statePulse =
                -0.05;

            break;

    }


    const audioPulse =
        NOVA.audioLevel *
        0.25;


    const coreScale =
        pulse +
        audioPulse +
        statePulse;


    const shellScale =
        pulse +
        audioPulse * 1.5 +
        statePulse * 1.5;


    if (core) {

        core.scale.setScalar(
            Math.max(
                coreScale,
                0.5
            )
        );

    }


    if (outerShell) {

        outerShell.scale.setScalar(
            Math.max(
                shellScale,
                0.5
            )
        );

    }


    /* ------------------------------------------------------
       PARTICLES
    ------------------------------------------------------ */

    if (particleMaterial) {

        let opacity =
            0.55 +
            NOVA.audioLevel * 0.35;


        if (
            NOVA.state ===
            "listening"
        ) {

            opacity +=
                0.20 +
                Math.sin(
                    animationTime * 8
                ) * 0.08;

        }


        else if (
            NOVA.state ===
            "thinking"
        ) {

            opacity +=
                0.10;

        }


        else if (
            NOVA.state ===
            "speaking"
        ) {

            opacity +=
                0.16;

        }


        particleMaterial.opacity =
            Math.min(
                opacity,
                1
            );

    }


    renderer.render(
        scene,
        camera
    );

}


/* ==========================================================
   RESIZE
========================================================== */

function resizeOrb() {

    if (
        !renderer ||
        !camera ||
        !orbContainer
    ) {

        return;

    }


    const width =
        Math.max(
            orbContainer.clientWidth,
            1
        );


    const height =
        Math.max(
            orbContainer.clientHeight,
            1
        );


    camera.aspect =
        width / height;


    camera.updateProjectionMatrix();


    renderer.setSize(
        width,
        height
    );

}


/* ==========================================================
   NOVA STATE
========================================================== */

function setNOVAState(
    newState
) {

    NOVA.state =
        newState;


    NOVA.listening =
        newState ===
        "listening";


    NOVA.thinking =
        newState ===
        "thinking";


    NOVA.speaking =
        newState ===
        "speaking";


    const labels = {

        idle:
            "STANDBY",

        listening:
            "LISTENING",

        thinking:
            "PROCESSING",

        speaking:
            "SPEAKING",

        paused:
            "PAUSED",

        error:
            "SYSTEM ERROR"

    };


    const label =
        labels[newState] ||
        "STANDBY";


    safeText(
        orbState,
        label
    );


    safeText(
        coreStatus,
        label
    );


    if (voiceStatus) {

        if (
            newState ===
            "listening"
        ) {

            voiceStatus.textContent =
                "LISTENING";

        }

        else if (
            newState ===
            "thinking"
        ) {

            voiceStatus.textContent =
                "PROCESSING";

        }

        else if (
            newState ===
            "speaking"
        ) {

            voiceStatus.textContent =
                "TRANSMITTING";

        }

        else {

            voiceStatus.textContent =
                "READY";

        }

    }


    if (voiceWave) {

        voiceWave.classList.toggle(
            "active",
            newState ===
            "listening" ||
            newState ===
            "speaking"
        );

    }


    if (orbContainer) {

        orbContainer.classList.remove(

            "nova-idle",

            "nova-listening",

            "nova-thinking",

            "nova-speaking",

            "nova-error",

            "nova-paused"

        );


        orbContainer.classList.add(
            `nova-${newState}`
        );

    }


    console.log(
        `[NOVA STATE] ${newState}`
    );

}


/* ==========================================================
   MESSAGES
========================================================== */

function addMessage(
    speaker,
    text,
    type = "nova",
    persist = true
) {

    if (!conversation)
        return;


    const message =
        document.createElement(
            "div"
        );


    message.className =
        `message ${type}`;


    const speakerElement =
        document.createElement(
            "span"
        );


    speakerElement.className =
        "speaker";


    speakerElement.textContent =
        speaker;


    const textElement =
        document.createElement(
            "span"
        );


    textElement.className =
        "text";


    textElement.textContent =
        text;


    message.appendChild(
        speakerElement
    );


    message.appendChild(
        textElement
    );


    conversation.appendChild(
        message
    );


    if (welcomeScreen) {

        welcomeScreen.classList.add(
            "hidden"
        );

    }


    conversation.scrollTop =
        conversation.scrollHeight;


    NOVA.messages++;


    safeText(
        messageCount,
        NOVA.messages
    );


    if (persist) {

        saveMessageToActiveChat(
            speaker,
            text,
            type
        );

    }

}


/* ==========================================================
   CHAT HISTORY
========================================================== */

function makeChatId() {

    return `chat-${Date.now()}-${Math.random().toString(16).slice(2)}`;

}


function createChat(
    title = "New chat"
) {

    return {

        id: makeChatId(),

        title,

        createdAt: Date.now(),

        updatedAt: Date.now(),

        messages: []

    };

}


function persistChatSessions() {

    try {

        localStorage.setItem(
            CHAT_STORAGE_KEY,
            JSON.stringify({
                activeChatId,
                sessions: chatSessions
            })
        );

    }

    catch (error) {

        console.warn(
            "[NOVA] Chat history could not be saved.",
            error
        );

    }

}


function getActiveChat() {

    return chatSessions.find(
        chat => chat.id === activeChatId
    ) || null;

}


function titleFromMessage(
    text
) {

    const clean = text
        .replace(/\s+/g, " ")
        .trim();

    if (clean.length <= 42)
        return clean;

    return `${clean.slice(0, 42).trim()}…`;

}


function saveMessageToActiveChat(
    speaker,
    text,
    type
) {

    let chat = getActiveChat();

    if (!chat) {

        chat = createChat();
        chatSessions.unshift(chat);
        activeChatId = chat.id;

    }

    chat.messages.push({
        speaker,
        text,
        type,
        timestamp: Date.now()
    });

    if (
        type === "user" &&
        (
            chat.title === "New chat" ||
            !chat.title
        )
    ) {

        chat.title = titleFromMessage(text);

    }

    chat.updatedAt = Date.now();

    chatSessions.sort(
        (a, b) => b.updatedAt - a.updatedAt
    );

    persistChatSessions();
    renderChatHistory();

}


function renderChatHistory() {

    if (!chatHistory)
        return;

    const query = chatSearch
        ? chatSearch.value.trim().toLowerCase()
        : "";

    const matches = chatSessions.filter(
        chat => chat.title.toLowerCase().includes(query)
    );

    chatHistory.replaceChildren();

    if (!matches.length) {

        const empty = document.createElement("div");
        empty.className = "history-empty";
        empty.textContent = query
            ? "No matching chats"
            : "Your conversations will appear here.";
        chatHistory.appendChild(empty);
        return;

    }

    matches.forEach(chat => {

        const item = document.createElement("div");
        item.className = `history-item${chat.id === activeChatId ? " active" : ""}`;

        const openButton = document.createElement("button");
        openButton.className = "history-button";
        openButton.type = "button";
        openButton.textContent = chat.title || "New chat";
        openButton.title = chat.title || "New chat";
        openButton.addEventListener("click", () => loadChat(chat.id));

        const deleteButton = document.createElement("button");
        deleteButton.className = "history-delete";
        deleteButton.type = "button";
        deleteButton.textContent = "×";
        deleteButton.title = "Delete chat";
        deleteButton.setAttribute("aria-label", `Delete ${chat.title}`);
        deleteButton.addEventListener("click", event => {
            event.stopPropagation();
            deleteChat(chat.id);
        });

        item.append(openButton, deleteButton);
        chatHistory.appendChild(item);

    });

}


function loadChat(
    chatId
) {

    const chat = chatSessions.find(
        item => item.id === chatId
    );

    if (!chat || !conversation)
        return;

    activeChatId = chat.id;

    conversation.querySelectorAll(".message").forEach(
        message => message.remove()
    );

    NOVA.messages = 0;
    safeText(messageCount, "0");

    if (welcomeScreen) {
        welcomeScreen.classList.toggle(
            "hidden",
            chat.messages.length > 0
        );
    }

    chat.messages.forEach(message => {
        addMessage(
            message.speaker,
            message.text,
            message.type,
            false
        );
    });

    persistChatSessions();
    renderChatHistory();
    closeMobileSidebar();

    if (commandInput)
        commandInput.focus();

}


function startNewChat() {

    const current = getActiveChat();

    if (
        current &&
        current.messages.length === 0
    ) {

        loadChat(current.id);
        return;

    }

    const chat = createChat();
    chatSessions.unshift(chat);
    activeChatId = chat.id;
    persistChatSessions();
    loadChat(chat.id);

}


function deleteChat(
    chatId
) {

    const deletingActiveChat =
        chatId === activeChatId;

    chatSessions = chatSessions.filter(
        chat => chat.id !== chatId
    );

    if (!chatSessions.length) {
        const replacement = createChat();
        chatSessions.push(replacement);
    }

    if (deletingActiveChat) {
        activeChatId = chatSessions[0].id;
        persistChatSessions();
        loadChat(activeChatId);
        return;
    }

    persistChatSessions();
    renderChatHistory();

}


function closeMobileSidebar() {

    if (sidebar)
        sidebar.classList.remove("mobile-open");

    if (mobileBackdrop)
        mobileBackdrop.classList.remove("visible");

}


function initializeChatHistory() {

    try {

        const saved = JSON.parse(
            localStorage.getItem(CHAT_STORAGE_KEY) || "null"
        );

        if (saved && Array.isArray(saved.sessions)) {
            chatSessions = saved.sessions;
            activeChatId = saved.activeChatId;
        }

    }

    catch (error) {

        console.warn(
            "[NOVA] Saved chat history was invalid.",
            error
        );

    }

    if (!chatSessions.length) {
        const firstChat = createChat();
        chatSessions = [firstChat];
        activeChatId = firstChat.id;
    }

    if (!getActiveChat())
        activeChatId = chatSessions[0].id;

    renderChatHistory();
    loadChat(activeChatId);

}


/* ==========================================================
   ACTIVITY
========================================================== */

function addActivity(
    text
) {

    if (!activity)
        return;


    const line =
        document.createElement(
            "div"
        );


    line.className =
        "activity-line";


    const dot =
        document.createElement(
            "span"
        );


    line.appendChild(
        dot
    );


    line.appendChild(
        document.createTextNode(
            text
        )
    );


    activity.prepend(
        line
    );


    while (
        activity.children.length >
        5
    ) {

        activity.removeChild(
            activity.lastChild
        );

    }

}


/* ==========================================================
   SEND COMMAND
========================================================== */

function sendCommand() {

    if (!commandInput)
        return;


    const text =
        commandInput.value.trim();


    if (!text)
        return;


    if (
        !window.nova ||
        !window.nova.isConnected()
    ) {

        addMessage(
            "SYSTEM",
            "NOVA backend is not connected.",
            "system"
        );


        addActivity(
            "BACKEND CONNECTION ERROR"
        );


        connectToNOVA();

        return;

    }


    addMessage(
        "YOU",
        text,
        "user"
    );


    addActivity(
        "COMMAND SENT TO NOVA CORE"
    );


    commandInput.value =
        "";


    commandInput.style.height =
        "auto";


    setNOVAState(
        "thinking"
    );


    NOVA.targetAudioLevel =
        0.12;


    try {

        window.nova.send({

            type:
                "command",

            text:
                text

        });

    }

    catch (error) {

        console.error(
            "[NOVA SEND ERROR]",
            error
        );


        setNOVAState(
            "error"
        );


        addActivity(
            "COMMAND TRANSMISSION FAILED"
        );

    }

}


/* ==========================================================
   MICROPHONE
========================================================== */

function activateMicrophone() {

    if (!window.nova) {

        addActivity(
            "ELECTRON BRIDGE UNAVAILABLE"
        );

        return;

    }


    if (
        !novaSocket ||
        novaSocket.readyState !==
        WebSocket.OPEN
    ) {

        addActivity(
            "NOVA BACKEND NOT CONNECTED"
        );


        connectToNOVA();

        return;

    }


    if (
        NOVA.state ===
        "speaking" ||
        NOVA.state ===
        "thinking"
    ) {

        return;

    }


    setNOVAState(
        "listening"
    );


    NOVA.targetAudioLevel =
        0.35;


    addActivity(
        "VOICE INPUT REQUESTED"
    );


    try {

        window.nova.send({

            type:
                "voice"

        });

    }

    catch (error) {

        console.error(
            "[NOVA VOICE ERROR]",
            error
        );


        NOVA.targetAudioLevel =
            0;


        setNOVAState(
            "error"
        );

    }

}


/* ==========================================================
   STOP SPEAKING
========================================================== */

function stopSpeaking() {

    if (!window.nova)
        return;


    try {

        window.nova.send({

            type:
                "stop_speaking"

        });


        addActivity(
            "NOVA SPEECH STOP REQUESTED"
        );


        NOVA.targetAudioLevel =
            0;


        setNOVAState(
            "idle"
        );

    }

    catch (error) {

        console.error(
            "[NOVA STOP ERROR]",
            error
        );

    }

}


/* ==========================================================
   EXIT
========================================================== */

function exitNOVA() {

    addActivity(
        "SHUTTING DOWN NOVA"
    );


    setNOVAState(
        "paused"
    );


    NOVA.targetAudioLevel =
        0;


    if (commandInput)
        commandInput.disabled = true;


    if (sendButton)
        sendButton.disabled = true;


    if (micButton)
        micButton.disabled = true;


    if (stopButton)
        stopButton.disabled = true;


    manuallyClosed =
        true;


    if (
        window.nova &&
        typeof window.nova.quit ===
        "function"
    ) {

        window.nova.quit();

    }

}


/* ==========================================================
   WINDOW CONTROLS
========================================================== */

function minimizeNOVA() {

    if (
        window.nova &&
        typeof window.nova.minimize ===
        "function"
    ) {

        window.nova.minimize();

    }

}


function maximizeNOVA() {

    if (
        window.nova &&
        typeof window.nova.maximize ===
        "function"
    ) {

        window.nova.maximize();

    }

}


/* ==========================================================
   BUTTON EVENTS
========================================================== */

if (sendButton) {

    sendButton.addEventListener(
        "click",
        sendCommand
    );

}


if (micButton) {

    micButton.addEventListener(
        "click",
        activateMicrophone
    );

}


if (stopButton) {

    stopButton.addEventListener(
        "click",
        stopSpeaking
    );

}


if (exitButton) {

    exitButton.addEventListener(
        "click",
        exitNOVA
    );

}


if (minimizeButton) {

    minimizeButton.addEventListener(
        "click",
        minimizeNOVA
    );

}


if (maximizeButton) {

    maximizeButton.addEventListener(
        "click",
        maximizeNOVA
    );

}


if (commandInput) {

    commandInput.addEventListener(
        "keydown",
        event => {

            if (
                event.key ===
                "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                sendCommand();

            }

        }
    );


    commandInput.addEventListener(
        "input",
        () => {

            commandInput.style.height = "auto";
            commandInput.style.height = `${Math.min(commandInput.scrollHeight, 180)}px`;

        }
    );

}


if (newChatButton) {

    newChatButton.addEventListener(
        "click",
        startNewChat
    );

}


if (chatSearch) {

    chatSearch.addEventListener(
        "input",
        renderChatHistory
    );

}


if (sidebarToggle && sidebar) {

    sidebarToggle.addEventListener(
        "click",
        () => {

            if (window.innerWidth <= 840) {
                closeMobileSidebar();
                return;
            }

            sidebar.classList.toggle("collapsed");

        }
    );

}


if (mobileSidebarButton && sidebar) {

    mobileSidebarButton.addEventListener(
        "click",
        () => {
            sidebar.classList.add("mobile-open");
            if (mobileBackdrop)
                mobileBackdrop.classList.add("visible");
        }
    );

}


if (mobileBackdrop) {

    mobileBackdrop.addEventListener(
        "click",
        closeMobileSidebar
    );

}


document.querySelectorAll(".prompt-card").forEach(
    prompt => {

        prompt.addEventListener(
            "click",
            () => {

                if (!commandInput)
                    return;

                commandInput.value = prompt.dataset.prompt || "";
                commandInput.focus();
                sendCommand();

            }
        );

    }
);


/* ==========================================================
   CLOCK
========================================================== */

function updateClock() {

    if (!systemTime)
        return;


    const now =
        new Date();


    systemTime.textContent =
        now.toLocaleTimeString(
            [],
            {
                hour12: false
            }
        );

}


setInterval(
    updateClock,
    1000
);


updateClock();


/* ==========================================================
   TELEMETRY
========================================================== */

function updateTelemetry() {

    const cpu =
        Math.floor(
            15 +
            Math.random() *
            25
        );


    const memory =
        Math.floor(
            35 +
            Math.random() *
            20
        );


    const battery =
        78;


    const cpuValue =
        document.getElementById(
            "cpu-value"
        );


    const memoryValue =
        document.getElementById(
            "memory-value"
        );


    const batteryValue =
        document.getElementById(
            "battery-value"
        );


    const cpuBar =
        document.getElementById(
            "cpu-bar"
        );


    const memoryBar =
        document.getElementById(
            "memory-bar"
        );


    const batteryBar =
        document.getElementById(
            "battery-bar"
        );


    safeText(
        cpuValue,
        `${cpu}%`
    );


    safeText(
        memoryValue,
        `${memory}%`
    );


    safeText(
        batteryValue,
        `${battery}%`
    );


    if (cpuBar)
        cpuBar.style.width =
            `${cpu}%`;


    if (memoryBar)
        memoryBar.style.width =
            `${memory}%`;


    if (batteryBar)
        batteryBar.style.width =
            `${battery}%`;

}


setInterval(
    updateTelemetry,
    2000
);


updateTelemetry();


/* ==========================================================
   AUDIO ANIMATION
========================================================== */

function animateAudio() {

    NOVA.audioLevel +=
        (
            NOVA.targetAudioLevel -
            NOVA.audioLevel
        ) * 0.12;


    requestAnimationFrame(
        animateAudio
    );

}


animateAudio();


/* ==========================================================
   CONNECT TO NOVA CORE
========================================================== */

function connectToNOVA() {

    if (
        manuallyClosed
    ) {

        return;

    }


    if (!window.nova) {

        console.error(
            "[NOVA] Electron bridge unavailable."
        );


        NOVA.connected =
            false;


        setNOVAState(
            "error"
        );


        return;

    }


    if (
        novaSocket &&
        (
            novaSocket.readyState ===
            WebSocket.OPEN ||
            novaSocket.readyState ===
            WebSocket.CONNECTING
        )
    ) {

        return;

    }


    addActivity(
        "CONNECTING TO NOVA CORE"
    );


    try {

        novaSocket =
            window.nova.connect();

    }

    catch (error) {

        console.error(
            "[NOVA CONNECTION ERROR]",
            error
        );


        NOVA.connected =
            false;


        setNOVAState(
            "error"
        );


        scheduleReconnect();

        return;

    }


    novaSocket.onopen =
        () => {

            console.log(
                "[NOVA] WebSocket connected."
            );


            NOVA.connected =
                true;


            addActivity(
                "NOVA CORE CONNECTION ESTABLISHED"
            );


            setNOVAState(
                "idle"
            );


            checkNOVAHealth();

        };


    novaSocket.onmessage =
        event => {

            try {

                const message =
                    JSON.parse(
                        event.data
                    );


                handleNOVAMessage(
                    message
                );

            }

            catch (error) {

                console.error(
                    "[NOVA MESSAGE ERROR]",
                    error
                );

            }

        };


    novaSocket.onerror =
        error => {

            console.error(
                "[NOVA SOCKET ERROR]",
                error
            );


            NOVA.connected =
                false;


            addActivity(
                "NOVA CORE CONNECTION ERROR"
            );


            setNOVAState(
                "error"
            );

        };


    novaSocket.onclose =
        () => {

            console.warn(
                "[NOVA] Backend disconnected."
            );


            NOVA.connected =
                false;


            if (!manuallyClosed) {

                addActivity(
                    "NOVA CORE DISCONNECTED"
                );


                setNOVAState(
                    "error"
                );


                scheduleReconnect();

            }

        };

}


/* ==========================================================
   RECONNECT
========================================================== */

function scheduleReconnect() {

    if (manuallyClosed)
        return;


    if (reconnectTimer)
        return;


    reconnectTimer =
        setTimeout(
            () => {

                reconnectTimer =
                    null;


                connectToNOVA();

            },
            2000
        );

}


/* ==========================================================
   MESSAGE HANDLER
========================================================== */

function handleNOVAMessage(
    message
) {

    console.log(
        "[NOVA EVENT]",
        message
    );


    switch (
        message.type
    ) {

        case "connected":

            NOVA.connected =
                true;


            addActivity(
                "NOVA CORE ONLINE"
            );


            setNOVAState(
                "idle"
            );


            break;


        case "status":

            handleNOVAStatus(
                message
            );


            break;


        case "response":

            handleNOVAResponse(
                message
            );


            break;


        case "transcript":

            if (
                message.text
            ) {

                addMessage(
                    "YOU",
                    message.text,
                    "user"
                );

            }


            break;


        case "error":

            console.error(
                "[NOVA BACKEND ERROR]",
                message.message
            );


            addMessage(
                "SYSTEM",
                message.message ||
                "Unknown NOVA backend error.",
                "system"
            );


            addActivity(
                "BACKEND ERROR"
            );


            NOVA.targetAudioLevel =
                0;


            setNOVAState(
                "error"
            );


            break;


        case "shutdown":

            manuallyClosed =
                true;


            addActivity(
                "NOVA CORE SHUTDOWN"
            );


            NOVA.targetAudioLevel =
                0;


            setNOVAState(
                "paused"
            );


            break;


        case "pong":

            break;


        default:

            console.log(
                "[NOVA] Unknown message:",
                message
            );

    }

}


/* ==========================================================
   STATUS HANDLER
========================================================== */

function handleNOVAStatus(
    message
) {

    const backendState =
        message.state;


    switch (
        backendState
    ) {

        case "listening":

            NOVA.targetAudioLevel =
                0.35;


            setNOVAState(
                "listening"
            );


            addActivity(
                "VOICE INPUT ACTIVE"
            );


            break;


        case "thinking":

            NOVA.targetAudioLevel =
                0.12;


            setNOVAState(
                "thinking"
            );


            addActivity(
                "NOVA PROCESSING"
            );


            break;


        case "speaking":

            NOVA.targetAudioLevel =
                0.65;


            setNOVAState(
                "speaking"
            );


            addActivity(
                "NOVA TRANSMITTING"
            );


            break;


        case "idle":

            NOVA.targetAudioLevel =
                0;


            setNOVAState(
                "idle"
            );


            break;


        default:

            console.log(
                "[NOVA] Unknown state:",
                backendState
            );

    }

}


/* ==========================================================
   RESPONSE HANDLER
========================================================== */

function handleNOVAResponse(
    message
) {

    const response =
        message.text;


    if (!response)
        return;


    addMessage(
        "NOVA",
        response,
        "nova"
    );


    addActivity(

        message.source ===
        "router"

            ? "TOOL EXECUTED"

            : "AI RESPONSE RECEIVED"

    );


    /*
     * Python handles TTS.
     *
     * We do NOT use browser speechSynthesis.
     */

}


/* ==========================================================
   HEALTH
========================================================== */

async function checkNOVAHealth() {

    if (
        !window.nova ||
        typeof window.nova.health !==
        "function"
    ) {

        return;

    }


    try {

        const health =
            await window.nova.health();


        console.log(
            "[NOVA HEALTH]",
            health
        );


        if (
            health.success
        ) {

            addActivity(
                `CORE v${health.version} ONLINE`
            );

        }

    }

    catch (error) {

        console.error(
            "[NOVA HEALTH ERROR]",
            error
        );


        addActivity(
            "CORE HEALTH CHECK FAILED"
        );

    }

}


/* ==========================================================
   INITIALIZATION
========================================================== */

function initializeNOVA() {

    console.log(
        "=================================================="
    );

    console.log(
        "NOVA DESKTOP CORE"
    );

    console.log(
        "Initializing..."
    );

    console.log(
        "=================================================="
    );


    initializeOrb();


    initializeChatHistory();


    setNOVAState(
        "idle"
    );


    addActivity(
        "NOVA CORE INITIALIZED"
    );


    connectToNOVA();

}


initializeNOVA();
