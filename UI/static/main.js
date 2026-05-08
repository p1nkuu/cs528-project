// Scene Setup
const scene = new THREE.Scene();

// Camera Setup
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(4, 3, 5);
camera.lookAt(0, 0, 0);

// Renderer Setup
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
// Soft rendering
renderer.outputEncoding = THREE.sRGBEncoding;
document.getElementById('canvas-container').appendChild(renderer.domElement);

// OrbitControls
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.enableZoom = true;
controls.enablePan = false;
// Lock vertical rotation (polar angle) so the "up" direction stays fixed
controls.minPolarAngle = Math.PI / 3; 
controls.maxPolarAngle = Math.PI / 3;

// Cube Parameters (1x1x1 logic, but we scale visually by 2 so coordinates are -1, 0, 1)
const size = 2; // Visual size

// Draw Wireframe Cube
const geometry = new THREE.BoxGeometry(size, size, size);
const edges = new THREE.EdgesGeometry(geometry);
const lineMaterial = new THREE.LineBasicMaterial({ color: 0x45a29e, linewidth: 2 });
const cubeLines = new THREE.LineSegments(edges, lineMaterial);
scene.add(cubeLines);

// Draw vertex nodes to emphasize the grid
const nodeGeo = new THREE.SphereGeometry(0.05, 16, 16);
const nodeMat = new THREE.MeshBasicMaterial({ color: 0x1f2833 });
const positions = [-1, 1];
for(let x of positions) {
    for(let y of positions) {
        for(let z of positions) {
            const node = new THREE.Mesh(nodeGeo, nodeMat);
            node.position.set(x, y, z);
            scene.add(node);
        }
    }
}

// Glowing Cursor
const cursorGeo = new THREE.SphereGeometry(0.15, 32, 32);
const cursorMat = new THREE.MeshBasicMaterial({ color: 0x66fcf1 });
const cursor = new THREE.Mesh(cursorGeo, cursorMat);

const trailMaterial = new THREE.LineBasicMaterial({
    color: 0x66fcf1,
    transparent: true,
    opacity: 0.9,
});
const trailGeometry = new THREE.BufferGeometry().setFromPoints([]);
const passwordTrail = new THREE.Line(trailGeometry, trailMaterial);
scene.add(passwordTrail);

// Add a glowing halo effect
const haloGeo = new THREE.SphereGeometry(0.25, 32, 32);
const haloMat = new THREE.MeshBasicMaterial({ 
    color: 0x66fcf1, 
    transparent: true, 
    opacity: 0.3 
});
const halo = new THREE.Mesh(haloGeo, haloMat);
cursor.add(halo);
scene.add(cursor);

// State tracking (logical grid from -1 to 1)
let gridPos = { x: -1, y: -1, z: 1 }; // Start at front-bottom-left
const PASSWORD_LENGTH = 6;
let trailPoints = [];

// Initial positioning
cursor.position.set(gridPos.x, gridPos.y, gridPos.z);
updateUI();

// Resize handler
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// Render Loop
function animate() {
    requestAnimationFrame(animate);
    
    controls.update(); // needed for damping
    
    // Pulsate halo
    const scale = 1 + Math.sin(Date.now() * 0.005) * 0.2;
    halo.scale.set(scale, scale, scale);

    renderer.render(scene, camera);
}
animate();

// WebSocket Connection
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/subscriber`);

const modeBanner = document.getElementById('mode-banner');
const authTitle = document.getElementById('auth-title');
const passwordNameInput = document.getElementById('password-name');
const primaryActionButton = document.getElementById('primary-action');
const secondaryActionButton = document.getElementById('secondary-action');
const recordingStatus = document.getElementById('recording-status');
const sequenceSlots = document.getElementById('sequence-slots');
const savedStatus = document.getElementById('saved-status');
const loginStatus = document.getElementById('login-status');

const AUTH_MODE = {
    UNLOCK: 'unlock',
    CREATE: 'create',
};

let authMode = AUTH_MODE.UNLOCK;
let isCapturing = false;
let capturedSequence = [];
let captureStartingPoint = null;

function setLoginStatus(message, state = '') {
    loginStatus.classList.remove('logged-in', 'login-failed');
    if (state) {
        loginStatus.classList.add(state);
    }
    loginStatus.innerText = message;
}

function setMode(mode) {
    authMode = mode;
    const isCreateMode = mode === AUTH_MODE.CREATE;

    passwordNameInput.style.display = isCreateMode ? 'block' : 'none';
    passwordNameInput.value = isCreateMode ? passwordNameInput.value : '';
    authTitle.innerText = isCreateMode ? 'Create New Password' : 'Unlock Device';
    modeBanner.innerText = isCreateMode ? 'Guided password creation' : 'Lock screen ready';
    recordingStatus.innerText = isCreateMode
        ? 'Status: name the password, then record 6 gestures'
        : 'Status: enter your password to unlock';
    primaryActionButton.innerText = isCreateMode ? 'Begin Creation' : 'Start Unlock';
    secondaryActionButton.innerText = isCreateMode ? 'Back to Unlock' : 'Create New Password';
}

function buildPasswordSlots() {
    sequenceSlots.innerHTML = '';
    for (let index = 0; index < PASSWORD_LENGTH; index += 1) {
        const slot = document.createElement('div');
        slot.className = 'sequence-slot';
        slot.innerText = String(index + 1);
        sequenceSlots.appendChild(slot);
    }
}

function renderCapturedSequence() {
    const slots = Array.from(sequenceSlots.children);
    slots.forEach((slot, index) => {
        slot.classList.remove('filled', 'locked');
        slot.innerText = index < capturedSequence.length ? capturedSequence[index].toUpperCase() : String(index + 1);
        if (index < capturedSequence.length) {
            slot.classList.add('filled');
        }
    });

    if (capturedSequence.length === PASSWORD_LENGTH) {
        slots.forEach((slot) => slot.classList.add('locked'));
    }
}

function updateTrail() {
    passwordTrail.geometry.dispose();
    passwordTrail.geometry = new THREE.BufferGeometry().setFromPoints(trailPoints);
}

function clearAttemptState() {
    isCapturing = false;
    capturedSequence = [];
    trailPoints.length = 0;
    trailPoints.push(new THREE.Vector3(gridPos.x, gridPos.y, gridPos.z));
    captureStartingPoint = null;
    updateTrail();
    renderCapturedSequence();
    primaryActionButton.disabled = false;
    secondaryActionButton.disabled = false;
    primaryActionButton.innerText = authMode === AUTH_MODE.CREATE ? 'Begin Creation' : 'Start Unlock';
}

function startCapture() {
    if (authMode === AUTH_MODE.CREATE && !passwordNameInput.value.trim()) {
        savedStatus.innerText = 'Enter a password name first.';
        return;
    }

    capturedSequence = [];
    trailPoints.length = 0;
    // Record the starting grid position for this capture
    captureStartingPoint = { x: gridPos.x, y: gridPos.y, z: gridPos.z };
    trailPoints.push(new THREE.Vector3(captureStartingPoint.x, captureStartingPoint.y, captureStartingPoint.z));
    updateTrail();
    renderCapturedSequence();
    isCapturing = true;
    primaryActionButton.disabled = true;
    secondaryActionButton.disabled = true;
    primaryActionButton.innerText = 'Recording...';
    savedStatus.innerText = authMode === AUTH_MODE.CREATE
        ? 'Move 6 gestures to save the new password.'
        : 'Move 6 gestures to unlock.';
    setLoginStatus('Not logged in');
    logEvent(authMode === AUTH_MODE.CREATE ? 'Password creation started' : 'Unlock attempt started');
}

function completeCapture() {
    isCapturing = false;
    primaryActionButton.disabled = false;
    primaryActionButton.innerText = authMode === AUTH_MODE.CREATE ? 'Begin Creation' : 'Start Unlock';

    if (authMode === AUTH_MODE.CREATE) {
        saveCapturedPassword();
    } else {
        verifyCapturedPassword();
    }
}

async function saveCapturedPassword() {
    const name = passwordNameInput.value.trim();
    try {
        const startingToSend = captureStartingPoint ?? (trailPoints.length ? { x: trailPoints[0].x, y: trailPoints[0].y, z: trailPoints[0].z } : { x: gridPos.x, y: gridPos.y, z: gridPos.z });

        const response = await fetch('/passwords/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, sequence: capturedSequence, starting_point: startingToSend }),
        });
        const payload = await response.json();

        if (payload.status === 'ok') {
            savedStatus.innerText = `Saved "${payload.saved.name}" to the computer.`;
            logEvent(`Password saved: ${payload.saved.name}`);
            setMode(AUTH_MODE.UNLOCK);
            isCapturing = false;
            primaryActionButton.disabled = false;
            primaryActionButton.innerText = 'Start Unlock';
        } else {
            savedStatus.innerText = payload.message || 'Could not save password.';
            clearAttemptState();
        }
    } catch (error) {
        savedStatus.innerText = 'Save failed. Check that the backend is running.';
        logEvent('Password save failed', true);
        clearAttemptState();
    }
}

async function verifyCapturedPassword() {
    try {
        const startingToSend = captureStartingPoint ?? (trailPoints.length ? { x: trailPoints[0].x, y: trailPoints[0].y, z: trailPoints[0].z } : { x: gridPos.x, y: gridPos.y, z: gridPos.z });

        const response = await fetch('/passwords/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sequence: capturedSequence, starting_point: startingToSend }),
        });
        const payload = await response.json();

        if (payload.status === 'ok' && payload.matched) {
            const userName = payload.user_name || 'User';
            setLoginStatus(`Logged in as ${userName}`, 'logged-in');
            savedStatus.innerText = 'Access granted.';
            logEvent(`Logged in as ${userName}`);
            isCapturing = false;
            primaryActionButton.disabled = false;
            primaryActionButton.innerText = 'Start Unlock';
            return;
        }

        setLoginStatus('Login failed. Try again.', 'login-failed');
        savedStatus.innerText = 'That password did not match. Try again.';
        logEvent('Unlock failed', true);
        clearAttemptState();
    } catch (error) {
        setLoginStatus('Login failed. Try again.', 'login-failed');
        savedStatus.innerText = 'Unable to verify password. Check the backend.';
        logEvent('Password verification failed', true);
        clearAttemptState();
    }
}

buildPasswordSlots();
setMode(AUTH_MODE.UNLOCK);

primaryActionButton.addEventListener('click', () => {
    if (!isCapturing) {
        startCapture();
    }
});

secondaryActionButton.addEventListener('click', () => {
    if (authMode === AUTH_MODE.CREATE) {
        setMode(AUTH_MODE.UNLOCK);
        clearAttemptState();
        savedStatus.innerText = 'Ready to unlock.';
    } else {
        setMode(AUTH_MODE.CREATE);
        clearAttemptState();
        passwordNameInput.focus();
        savedStatus.innerText = 'Enter a password name, then begin creation.';
    }
});

passwordNameInput.addEventListener('input', () => {
    if (authMode === AUTH_MODE.CREATE) {
        savedStatus.innerText = passwordNameInput.value.trim()
            ? 'Name set. Press Begin Creation when ready.'
            : 'Enter a password name first.';
    }
});

renderCapturedSequence();

ws.onopen = () => {
    console.log("WebSocket connected.");
    logEvent("Connected to Inference Engine");
};

ws.onmessage = (event) => {
    const action = event.data.toLowerCase().trim();
    console.log("Received action:", action);
    handleAction(action);
};

ws.onclose = () => {
    console.log("WebSocket disconnected.");
    logEvent("Disconnected", true);
};

// Movement Logic
function handleAction(action) {
    let moved = false;
    let target = { x: gridPos.x, y: gridPos.y, z: gridPos.z };

    // Map actions to grid coordinates
    // Up/Down = Y axis
    // Right/Left = X axis
    // Forward/Backward = Z axis
    switch(action) {
        case 'up':
            if(target.y < 1) { target.y += 2; moved = true; }
            break;
        case 'down':
            if(target.y > -1) { target.y -= 2; moved = true; }
            break;
        case 'right':
            if(target.x < 1) { target.x += 2; moved = true; }
            break;
        case 'left':
            if(target.x > -1) { target.x -= 2; moved = true; }
            break;
        case 'forward':
            // "Forward" usually means deeper into the screen (Z decreases)
            if(target.z > -1) { target.z -= 2; moved = true; }
            break;
        case 'backward':
            // "Backward" means pulling towards user (Z increases)
            if(target.z < 1) { target.z += 2; moved = true; }
            break;
        default:
            console.log("Unknown action:", action);
            return;
    }

    if(moved) {
        // Update state
        const previousPosition = { ...gridPos };
        gridPos = target;

        if (isCapturing && capturedSequence.length < PASSWORD_LENGTH) {
            capturedSequence.push(action);
            renderCapturedSequence();
            trailPoints.push(new THREE.Vector3(gridPos.x, gridPos.y, gridPos.z));
            updateTrail();

            if (capturedSequence.length === PASSWORD_LENGTH) {
                recordingStatus.innerText = 'Status: validating password';
                logEvent('Password input reached 6 gestures');
                completeCapture();
            }
        }
        
        // Animate movement using GSAP
        gsap.to(cursor.position, {
            x: gridPos.x,
            y: gridPos.y,
            z: gridPos.z,
            duration: 0.3,
            ease: "back.out(1.5)"
        });

        // UI Updates
        updateUI(action);
        logEvent(`Moved ${action.toUpperCase()}`);
        
        // Flash cube edges on success
        flashEdges(0x66fcf1);
    } else {
        // Hit boundary
        logEvent(`Blocked: ${action.toUpperCase()} (Boundary hit)`);
        flashEdges(0xff4444); // Red flash for block
        
        // Small jiggle animation to indicate failure
        let dir = { x: 0, y: 0, z: 0 };
        if(action === 'up') dir.y = 0.2;
        if(action === 'down') dir.y = -0.2;
        if(action === 'right') dir.x = 0.2;
        if(action === 'left') dir.x = -0.2;
        if(action === 'forward') dir.z = -0.2;
        if(action === 'backward') dir.z = 0.2;

        gsap.to(cursor.position, {
            x: gridPos.x + dir.x,
            y: gridPos.y + dir.y,
            z: gridPos.z + dir.z,
            duration: 0.1,
            yoyo: true,
            repeat: 1
        });
    }
}

function updateUI(action = "none") {
    const el = document.getElementById('last-action');
    el.innerText = action;
    
    // Trigger CSS animation reflow
    el.classList.remove('flash');
    void el.offsetWidth;
    el.classList.add('flash');

    // Convert -1/1 coordinates back to 0/1 for easier reading
    const dispX = (gridPos.x + 1) / 2;
    const dispY = (gridPos.y + 1) / 2;
    const dispZ = (gridPos.z + 1) / 2; // Notice forward is z=0, backward is z=1

    document.getElementById('x-coord').innerText = dispX;
    document.getElementById('y-coord').innerText = dispY;
    document.getElementById('z-coord').innerText = Math.abs(dispZ - 1); // Flip Z so 1 is forward
}

function logEvent(msg, isError = false) {
    const logs = document.getElementById('logs');
    const li = document.createElement('li');
    li.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
    if(isError) li.style.color = '#ff4444';
    
    logs.insertBefore(li, logs.firstChild);
    
    // Keep max 5 items
    if(logs.children.length > 5) {
        logs.removeChild(logs.lastChild);
    }
}

function flashEdges(colorHex) {
    // Initial color change
    lineMaterial.color.setHex(colorHex);
    // Tween back to normal
    gsap.to(lineMaterial.color, {
        r: 69 / 255,   // 0x45
        g: 162 / 255, // 0xa2
        b: 158 / 255, // 0x9e
        duration: 0.5
    });
}
