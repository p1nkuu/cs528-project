let currentProgressStep = 0;
const maxProgressSteps = 6;

function updateProgressBar(step) {
    currentProgressStep = Math.min(step, maxProgressSteps);
    const segments = document.querySelectorAll('.progress-segment');
    segments.forEach((segment, index) => {
        segment.classList.remove('active');
        segment.classList.remove('completed');
        if (index < currentProgressStep - 1) {
            segment.classList.add('completed');
        } else if (index === currentProgressStep - 1) {
            segment.classList.add('active');
        }
    });
}

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

    // Normalize action to lowercase for comparison
    const normalizedAction = action.toLowerCase().trim();

    // Map actions to grid coordinates
    // Up/Down = Y axis
    // Right/Left = X axis
    // Forward/Backward = Z axis
    switch(normalizedAction) {
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

    if (currentProgressStep < 6) {
        updateProgressBar(currentProgressStep + 1);
    }

    if(moved) {
        // Update state
        gridPos = target;
        
        // Animate movement using GSAP
        gsap.to(cursor.position, {
            x: gridPos.x,
            y: gridPos.y,
            z: gridPos.z,
            duration: 0.3,
            ease: "back.out(1.5)"
        });

        // UI Updates
        updateUI(normalizedAction);
        logEvent(`Moved ${normalizedAction.toUpperCase()}`);
        
        // Flash cube edges on success
        flashEdges(0x66fcf1);
    } else {
        // Hit boundary
        logEvent(`Blocked: ${normalizedAction.toUpperCase()} (Boundary hit)`);
        flashEdges(0xff4444); // Red flash for block
        
        // Small jiggle animation to indicate failure
        let dir = { x: 0, y: 0, z: 0 };
        if(normalizedAction === 'up') dir.y = 0.2;
        if(normalizedAction === 'down') dir.y = -0.2;
        if(normalizedAction === 'right') dir.x = 0.2;
        if(normalizedAction === 'left') dir.x = -0.2;
        if(normalizedAction === 'forward') dir.z = -0.2;
        if(normalizedAction === 'backward') dir.z = 0.2;

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
