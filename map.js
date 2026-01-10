class HospitalDroneTracker {
    constructor() {
        this.viewMode = '3d'; // '3d' or '2d'
        this.selectedFloor = null; // 1 or 2
        this.selectedDrone = null;
        
        // Mock drone data - REPLACE THIS WITH YOUR BACKEND API CALL
        this.drones = [
            { id: 'D1', floor: 1, x: 200, y: 150, color: '#FF6B6B', name: 'Delivery Drone 1', status: 'Active' },
            { id: 'D2', floor: 1, x: 600, y: 300, color: '#4ECDC4', name: 'Medical Supply Drone', status: 'Active' },
            { id: 'D3', floor: 2, x: 400, y: 200, color: '#95E1D3', name: 'Emergency Drone', status: 'Standby' },
            { id: 'D4', floor: 1, x: 800, y: 400, color: '#FFE66D', name: 'Lab Sample Drone', status: 'Active' },
        ];
        
        // Store flight information for movement simulation
        this.droneFlights = {}; // drone_id -> { route, startTime, speed, is_emergency }

        // Three.js objects
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null; // OrbitControls
        this.animationId = null;
        this.droneMeshes = [];

        // DOM elements
        this.canvas = document.getElementById('three-canvas');
        this.canvasContainer = document.getElementById('canvas-container');
        this.floorPlanContainer = document.getElementById('floor-plan-container');
        this.floorSvg = document.getElementById('floor-svg');
        this.floorTitle = document.getElementById('floor-title');
        this.droneInfo = document.getElementById('drone-info');
        this.controlsContainer = document.getElementById('tracker-controls');

        // Check if required elements exist
        if (!this.canvas) {
            console.error('Map initialization failed: Canvas element (three-canvas) not found');
            return;
        }
        if (!this.canvasContainer) {
            console.error('Map initialization failed: Canvas container not found');
            return;
        }
        if (!this.floorSvg) {
            console.error('Map initialization failed: Floor SVG element not found');
            return;
        }

        console.log('Map DOM elements found successfully');

        // Ensure canvas has proper dimensions
        // Wait for container to have dimensions if needed
        const rect = this.canvasContainer.getBoundingClientRect();
        let containerWidth = rect.width || this.canvasContainer.clientWidth;
        let containerHeight = rect.height || this.canvasContainer.clientHeight;
        
        // If container has zero dimensions, use defaults and force a resize
        if (!containerWidth || containerWidth === 0) {
            containerWidth = 800;
            this.canvasContainer.style.width = containerWidth + 'px';
        }
        if (!containerHeight || containerHeight === 0) {
            containerHeight = 500;
            this.canvasContainer.style.height = containerHeight + 'px';
        }
        
        // Ensure minimum dimensions
        const width = Math.max(containerWidth, 400);
        const height = Math.max(containerHeight, 300);
        
        // Set canvas dimensions
        this.canvas.width = width;
        this.canvas.height = height;
        this.canvas.style.width = width + 'px';
        this.canvas.style.height = height + 'px';
        this.canvas.style.display = 'block';
        
        console.log(`Canvas dimensions set to: ${width}x${height}`);
        
        // Store dimensions for later use
        this.canvasWidth = width;
        this.canvasHeight = height;

        this.init();
    }

    init() {
        this.setupControls();
        this.init3DView();
        this.startDroneSimulation();
        this.setupEventListeners();
    }

    setupControls() {
        // Controls are initially hidden in 3D mode
        this.updateControls();
    }

    updateControls() {
        this.controlsContainer.innerHTML = '';
        
        // Always show Back to 3D button (disabled/grayed out when already in 3D view)
        const backBtn = document.createElement('button');
        backBtn.className = `tracker-button ${this.viewMode === '3d' ? 'disabled' : ''}`;
        backBtn.textContent = 'Back to 3D View';
        backBtn.onclick = () => {
            if (this.viewMode !== '3d') {
                this.switchTo3DView();
            }
        };
        if (this.viewMode === '3d') {
            backBtn.disabled = true;
            backBtn.style.opacity = '0.5';
            backBtn.style.cursor = 'not-allowed';
        }
        this.controlsContainer.appendChild(backBtn);

        // Always show Floor 1 button
        const floor1Btn = document.createElement('button');
        floor1Btn.className = `tracker-button ${this.selectedFloor === 1 ? 'active' : ''}`;
        floor1Btn.textContent = 'Floor 1';
        floor1Btn.onclick = () => {
            if (this.viewMode === '3d') {
                this.switchTo2DView(1);
            } else {
                this.switchFloor(1);
            }
        };
        this.controlsContainer.appendChild(floor1Btn);

        // Always show Floor 2 button
        const floor2Btn = document.createElement('button');
        floor2Btn.className = `tracker-button ${this.selectedFloor === 2 ? 'active' : ''}`;
        floor2Btn.textContent = 'Floor 2';
        floor2Btn.onclick = () => {
            if (this.viewMode === '3d') {
                this.switchTo2DView(2);
            } else {
                this.switchFloor(2);
            }
        };
        this.controlsContainer.appendChild(floor2Btn);
    }

    init3DView() {
        // Check if THREE is loaded
        if (typeof THREE === 'undefined') {
            console.error('Three.js is not loaded. Please check the script tags.');
            return;
        }
        
        console.log('Three.js loaded, initializing 3D view...');

        // Get canvas dimensions - use stored dimensions or current canvas size
        const width = this.canvasWidth || this.canvas.width || this.canvas.clientWidth || 800;
        const height = this.canvasHeight || this.canvas.height || this.canvas.clientHeight || 500;
        
        // Ensure canvas has proper dimensions
        if (this.canvas.width !== width || this.canvas.height !== height) {
            this.canvas.width = width;
            this.canvas.height = height;
        }
        
        console.log(`Initializing 3D view with dimensions: ${width}x${height}`);

        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);

        // Create camera
        this.camera = new THREE.PerspectiveCamera(
            75,
            width / height || 1.6,
            0.1,
            1000
        );
        this.camera.position.set(0, 15, 20);
        this.camera.lookAt(0, 0, 0);

        // Create renderer
        try {
            this.renderer = new THREE.WebGLRenderer({ 
                canvas: this.canvas, 
                antialias: true,
                alpha: false,
                powerPreference: "high-performance"
            });
            this.renderer.setSize(width, height);
            this.renderer.setPixelRatio(window.devicePixelRatio || 1);
            this.renderer.setClearColor(0xf0f0f0, 1); // Light gray background
            
            // Verify WebGL context was created
            const gl = this.canvas.getContext('webgl') || this.canvas.getContext('experimental-webgl');
            if (!gl) {
                console.error('WebGL context not available!');
                // Show error message on canvas
                this.canvasContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: red;">WebGL is not supported in your browser. Please update your browser or enable WebGL.</div>';
                return;
            }
            
            console.log('WebGL renderer created successfully');
            console.log('WebGL context:', gl.getParameter(gl.VERSION));
        } catch (error) {
            console.error('Failed to create WebGL renderer:', error);
            // Show error message
            if (this.canvasContainer) {
                this.canvasContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: red;">Failed to initialize 3D map: ' + error.message + '</div>';
            }
            return;
        }

        // Add OrbitControls - check if it's available
        if (typeof THREE.OrbitControls !== 'undefined') {
            this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        } else if (typeof OrbitControls !== 'undefined') {
            this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        } else {
            console.warn('OrbitControls not found. Map will work but without camera controls.');
            this.controls = null;
        }
        
        if (this.controls) {
            this.controls.enableDamping = true; // Smooth camera movement
            this.controls.dampingFactor = 0.05;
            this.controls.minDistance = 10; // Minimum zoom
            this.controls.maxDistance = 50; // Maximum zoom
            this.controls.maxPolarAngle = Math.PI / 2; // Prevent going below ground
        }

        // Add lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 20, 10);
        this.scene.add(directionalLight);

        // Create Floor 1 (Blue) - Properly aligned
        // Floor is 20 units wide (x: -10 to +10) and 12 units deep (z: -6 to +6)
        const floor1Geometry = new THREE.BoxGeometry(20, 0.5, 12);
        const floor1Material = new THREE.MeshPhongMaterial({ color: 0x3498db });
        const floor1 = new THREE.Mesh(floor1Geometry, floor1Material);
        floor1.position.set(0, 0.25, 0); // Center at origin, half thickness up for top surface at y=0
        floor1.userData = { floor: 1, clickable: true };
        this.scene.add(floor1);

        // Floor 1 edges - aligned with floor mesh
        const floor1Edge = new THREE.EdgesGeometry(floor1Geometry);
        const floor1Line = new THREE.LineSegments(floor1Edge, new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 2 }));
        floor1Line.position.set(0, 0.25, 0); // Same position as floor
        this.scene.add(floor1Line);

        // Create Floor 2 (Green) - Properly aligned directly above Floor 1
        // Same dimensions, positioned 6 units above Floor 1
        const floor2Geometry = new THREE.BoxGeometry(20, 0.5, 12);
        const floor2Material = new THREE.MeshPhongMaterial({ color: 0x2ecc71 });
        const floor2 = new THREE.Mesh(floor2Geometry, floor2Material);
        floor2.position.set(0, 6.25, 0); // 6 units above Floor 1 center, half thickness up
        floor2.userData = { floor: 2, clickable: true };
        this.scene.add(floor2);

        // Floor 2 edges - aligned with floor mesh
        const floor2Edge = new THREE.EdgesGeometry(floor2Geometry);
        const floor2Line = new THREE.LineSegments(floor2Edge, new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 2 }));
        floor2Line.position.set(0, 6.25, 0); // Same position as floor
        this.scene.add(floor2Line);
        
        // Add supporting pillars to make alignment clearer (optional visual aid)
        const pillarGeometry = new THREE.BoxGeometry(0.5, 6, 0.5);
        const pillarMaterial = new THREE.MeshPhongMaterial({ color: 0x888888 });
        // Add 4 corner pillars
        const pillarPositions = [
            [-9.75, 3, -5.75],  // Front-left
            [9.75, 3, -5.75],   // Front-right
            [-9.75, 3, 5.75],   // Back-left
            [9.75, 3, 5.75]     // Back-right
        ];
        pillarPositions.forEach(pos => {
            const pillar = new THREE.Mesh(pillarGeometry, pillarMaterial);
            pillar.position.set(pos[0], pos[1], pos[2]);
            this.scene.add(pillar);
        });

        // Add drones
        this.updateDroneMeshes();
        
        console.log('3D scene initialized with floors and drones');
        console.log('Scene children count:', this.scene.children.length);
        console.log('Renderer:', this.renderer ? 'OK' : 'MISSING');
        console.log('Camera:', this.camera ? 'OK' : 'MISSING');

        // Do an initial render to ensure something shows up
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
            console.log('Initial render completed');
        }

        // Start animation
        this.animate();
        console.log('Animation loop started');
    }

    updateDroneMeshes() {
        // Remove old drone meshes
        this.droneMeshes.forEach(mesh => this.scene.remove(mesh));
        this.droneMeshes = [];

        // Add new drone meshes
        this.drones.forEach(drone => {
            // Determine color: red for emergency, blue for normal
            let droneColor = 0x4ECDC4; // Default blue
            if (drone.emergency_drone) {
                droneColor = 0xFF0000; // Red for emergency
            } else {
                droneColor = 0x0066FF; // Blue for normal
            }
            
            const geometry = new THREE.SphereGeometry(0.4, 16, 16); // Slightly larger for visibility
            const material = new THREE.MeshPhongMaterial({ 
                color: droneColor,
                emissive: droneColor,
                emissiveIntensity: 0.3 // Make drones glow slightly for visibility
            });
            const sphere = new THREE.Mesh(geometry, material);
            
            // Get floor (1 or 2)
            const floor = drone.floor || 1;
            
            // Calculate current position along route (from map pixels to 3D coordinates)
            const currentPos = this.calculateDronePosition(drone);
            
            // Convert map coordinates (0-1000 for x, 0-600 for y) to 3D scene coordinates
            // Map x: 0-1000 -> 3D x: -10 to +10 (floor width is 20 units)
            // Map y: 0-600 -> 3D z: -6 to +6 (floor depth is 12 units)
            // Map y coordinate becomes z coordinate in 3D (depth)
            const x3d = (currentPos.x / 50) - 10;  // Map x -> 3D x
            const z3d = (currentPos.y / 50) - 6;   // Map y -> 3D z (depth)
            const y3d = floor === 1 ? 0.5 : 6.5;   // Height above floor (0.25 floor height + 0.25 clearance)
            
            sphere.position.set(x3d, y3d, z3d);
            sphere.userData = { 
                droneId: drone.id || drone.drone_id, 
                droneData: drone,
                // Mark as drone so OrbitControls can ignore it
                isDrone: true
            };
            // Remove onclick - clicks will be handled by raycaster in onCanvasClick
            // This prevents interference with drone movement
            this.scene.add(sphere);
            this.droneMeshes.push(sphere);
        });
    }

    animate() {
        if (!this.renderer || !this.scene || !this.camera) {
            console.warn('Animation skipped: renderer, scene, or camera not initialized');
            return; // Don't animate if not initialized
        }

        this.animationId = requestAnimationFrame(() => this.animate());

        // Update OrbitControls (camera movement only, doesn't affect drones)
        if (this.controls) {
            this.controls.update();
        }

        // Update drone positions in 3D (continuous movement, independent of mouse interactions)
        // Drones continue moving along their paths regardless of mouse position or clicks
        this.drones.forEach((drone, index) => {
            if (this.droneMeshes[index]) {
                // Calculate current position along route if drone is in transit
                // This position is based purely on elapsed time and speed, not mouse interactions
                const currentPos = this.calculateDronePosition(drone);
                const yPos = (drone.floor || 1) === 1 ? 0.5 : 6.5;
                
                // Update mesh position directly - this doesn't interfere with OrbitControls
                // OrbitControls only affect the camera, not individual objects
                // Convert map coordinates to 3D coordinates
                const floor = (drone.floor || 1);
                const x3d = (currentPos.x / 50) - 10;  // Map x -> 3D x
                const z3d = (currentPos.y / 50) - 6;   // Map y -> 3D z (depth)
                const y3d = floor === 1 ? 0.5 : 6.5;   // Height above floor
                
                this.droneMeshes[index].position.set(x3d, y3d, z3d);
                
                    // Store drone data reference for click detection (for info display only)
                // This doesn't affect position calculation - positions are purely time-based
                if (!this.droneMeshes[index].userData.droneData) {
                    this.droneMeshes[index].userData.droneData = drone;
                }
                
                // Update droneData in real-time for accurate info display
                // But position is calculated independently based on time and speed
                this.droneMeshes[index].userData.droneData = drone;
            }
        });
        
        // Important: Drone positions are calculated purely based on elapsed time and speed
        // Mouse interactions (hover, click) do NOT affect position calculations
        // OrbitControls only move the camera, not the drones themselves

        // Render the scene - this is critical for the map to show!
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        } else {
            console.error('Cannot render: renderer, scene, or camera is missing!', {
                renderer: !!this.renderer,
                scene: !!this.scene,
                camera: !!this.camera
            });
        }
    }

    setupEventListeners() {
        // Canvas click for floor selection
        this.canvas.addEventListener('click', (event) => this.onCanvasClick(event));

        // Close drone info
        document.getElementById('close-drone-info').addEventListener('click', () => {
            this.selectedDrone = null;
            this.droneInfo.style.display = 'none';
        });

        // Window resize
        window.addEventListener('resize', () => this.onWindowResize());
    }

    onCanvasClick(event) {
        if (this.viewMode !== '3d') return;

        const rect = this.canvas.getBoundingClientRect();
        const mouse = new THREE.Vector2(
            ((event.clientX - rect.left) / rect.width) * 2 - 1,
            -((event.clientY - rect.top) / rect.height) * 2 + 1
        );

        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(mouse, this.camera);
        
        // First check for drone clicks (don't affect their movement, just show info)
        const droneIntersects = raycaster.intersectObjects(this.droneMeshes);
        if (droneIntersects.length > 0) {
            const clickedDrone = droneIntersects[0].object;
            // Use droneData if available, otherwise find drone by ID
            if (clickedDrone.userData.droneData) {
                this.showDroneInfo(clickedDrone.userData.droneData);
            } else if (clickedDrone.userData.droneId) {
                const drone = this.drones.find(d => (d.id || d.drone_id) === clickedDrone.userData.droneId || `D${d.id || d.drone_id}` === clickedDrone.userData.droneId);
                if (drone) {
                    this.showDroneInfo(drone);
                }
            }
            // Return early - don't check for floor clicks when drone is clicked
            return;
        }
        
        // Check for floor clicks only if no drone was clicked
        const floorObjects = this.scene.children.filter(o => o.userData.clickable && o.userData.floor);
        const floorIntersects = raycaster.intersectObjects(floorObjects);
        if (floorIntersects.length > 0) {
            const obj = floorIntersects[0].object;
            if (obj.userData.clickable && obj.userData.floor) {
                this.switchTo2DView(obj.userData.floor);
            }
        }
    }

    onWindowResize() {
        if (this.viewMode === '3d') {
            this.camera.aspect = this.canvas.clientWidth / this.canvas.clientHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);
            if (this.controls) {
                this.controls.update();
            }
        }
    }

    switchTo2DView(floor) {
        this.viewMode = '2d';
        this.selectedFloor = floor;
        this.canvasContainer.style.display = 'none';
        this.floorPlanContainer.style.display = 'flex';
        this.updateControls();
        this.render2DFloor();
    }

    switchTo3DView() {
        this.viewMode = '3d';
        this.selectedFloor = null;
        this.selectedDrone = null;
        this.canvasContainer.style.display = 'flex';
        this.floorPlanContainer.style.display = 'none';
        this.droneInfo.style.display = 'none';
        this.updateControls();
    }

    switchFloor(floor) {
        this.selectedFloor = floor;
        this.selectedDrone = null;
        this.droneInfo.style.display = 'none';
        this.updateControls();
        this.render2DFloor();
    }

    createSVGElement(type, attributes) {
    const element = document.createElementNS('http://www.w3.org/2000/svg', type);
    for (const [key, value] of Object.entries(attributes)) {
        element.setAttribute(key, value);
    }
    return element;}

    render2DFloor() {
    while (this.floorSvg.firstChild) {
        this.floorSvg.removeChild(this.floorSvg.firstChild);
    }
    
    if (this.selectedFloor === 1) {
        this.renderFloor1();
    } else if (this.selectedFloor === 2) {
        this.renderFloor2();
    }}

    renderFloor1() {
    this.floorTitle.textContent = 'Floor 1 - Main Hospital Floor';
    
    // Outer border
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '10', y: '10', width: '980', height: '580',
        fill: '#fff', stroke: '#333', 'stroke-width': '2'
    }));

    // Pharmacy (Location 3) - Clickable
    const pharmRect = this.createSVGElement('rect', {
        x: '20', y: '20', width: '150', height: '120',
        fill: '#e8f4f8', stroke: '#333'
    });
    pharmRect.style.cursor = 'pointer';
    pharmRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(3, 'Pharmacy');
        }
    };
    this.floorSvg.appendChild(pharmRect);
    const pharmacyText = this.createSVGElement('text', {
        x: '95', y: '80', 'text-anchor': 'middle', 'font-size': '12'
    });
    pharmacyText.textContent = 'Pharmacy';
    this.floorSvg.appendChild(pharmacyText);

    // Stairs (Non-clickable)
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '180', y: '20', width: '50', height: '80',
        fill: '#d4d4d4', stroke: '#333'
    }));
    const stairsText = this.createSVGElement('text', {
        x: '205', y: '65', 'text-anchor': 'middle', 'font-size': '10'
    });
    stairsText.textContent = 'Stairs';
    this.floorSvg.appendChild(stairsText);

    // Elevator (Non-clickable)
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '240', y: '20', width: '50', height: '80',
        fill: '#d4d4d4', stroke: '#333'
    }));
    const elevText = this.createSVGElement('text', {
        x: '265', y: '60', 'text-anchor': 'middle', 'font-size': '10'
    });
    elevText.textContent = 'Elevator';
    this.floorSvg.appendChild(elevText);

    // Imaging (Radiology / CT / X-ray) - Clickable (Location 4)
    const imagingRect = this.createSVGElement('rect', {
        x: '180', y: '20', width: '120', height: '120',
        fill: '#e3f2fd', stroke: '#333'
    });
    imagingRect.style.cursor = 'pointer';
    imagingRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(4, 'Imaging');
        }
    };
    this.floorSvg.appendChild(imagingRect);
    let imagingText = this.createSVGElement('text', {
        x: '240', y: '85', 'text-anchor': 'middle', 'font-size': '11'
    });
    imagingText.textContent = 'Imaging';
    this.floorSvg.appendChild(imagingText);

    // Lab rooms: Specialized Lab Rooms - Clickable (Location 4)
    const labRect = this.createSVGElement('rect', {
        x: '310', y: '480', width: '360', height: '100',
        fill: '#e8f5e9', stroke: '#333'
    });
    labRect.style.cursor = 'pointer';
    labRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(4, 'Specialized Lab Rooms');
        }
    };
    this.floorSvg.appendChild(labRect);
    let labText = this.createSVGElement('text', {
        x: '490', y: '540', 'text-anchor': 'middle', 'font-size': '10'
    });
    labText.textContent = 'Specialized Lab Rooms';
    this.floorSvg.appendChild(labText);

    // Drone Storage - Clickable (for charging stations, could be location 9+)
    const droneStorageRect = this.createSVGElement('rect', {
        x: '230', y: '480', width: '70', height: '100',
        fill: '#acceccff', stroke: '#333'
    });
    droneStorageRect.style.cursor = 'pointer';
    droneStorageRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(9, 'Drone Storage');
        }
    };
    this.floorSvg.appendChild(droneStorageRect);
    let dronestorageText = this.createSVGElement('text', {
        x: '265', y: '530', 'text-anchor': 'middle', 'font-size': '10'
    });
    dronestorageText.textContent = 'Drone Storage';
    this.floorSvg.appendChild(dronestorageText);

    // General Ward - Clickable (Location 6)
    const generalRect = this.createSVGElement('rect', {
        x: '310', y: '20', width: '300', height: '120',
        fill: '#fffde7', stroke: '#333'
    });
    generalRect.style.cursor = 'pointer';
    generalRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(6, 'General Ward');
        }
    };
    this.floorSvg.appendChild(generalRect);
    let generalText = this.createSVGElement('text', {
        x: '460', y: '85', 'text-anchor': 'middle', 'font-size': '11'
    });
    generalText.textContent = 'General Ward';
    this.floorSvg.appendChild(generalText);

    // Diagnostic Rooms - Clickable (could be Location 7)
    const diagRect = this.createSVGElement('rect', {
        x: '310', y: '150', width: '300', height: '90',
        fill: '#fce4ec', stroke: '#333'
    });
    diagRect.style.cursor = 'pointer';
    diagRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(7, 'Diagnostic Rooms');
        }
    };
    this.floorSvg.appendChild(diagRect);
    let diagText = this.createSVGElement('text', {
        x: '460', y: '205', 'text-anchor': 'middle', 'font-size': '11'
    });
    diagText.textContent = 'Diagnostic Rooms';
    this.floorSvg.appendChild(diagText);

    // Occupational Therapy Area - Clickable (Location 7)
    const otRect = this.createSVGElement('rect', {
        x: '630', y: '100', width: '140', height: '90',
        fill: '#ede7f6', stroke: '#333'
    });
    otRect.style.cursor = 'pointer';
    otRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(7, 'Occupational Therapy');
        }
    };
    this.floorSvg.appendChild(otRect);
    let otText = this.createSVGElement('text', {
        x: '700', y: '150', 'text-anchor': 'middle', 'font-size': '10'
    });
    otText.textContent = 'Occupational Therapy';
    this.floorSvg.appendChild(otText);

    // Waiting Area pt2 - Clickable
    const wait2Rect = this.createSVGElement('rect', {
        x: '630', y: '200', width: '140', height: '60',
        fill: '#ede7f6', stroke: '#333'
    });
    wait2Rect.style.cursor = 'pointer';
    wait2Rect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(5, 'Waiting Area');
        }
    };
    this.floorSvg.appendChild(wait2Rect);
    let wait2Text = this.createSVGElement('text', {
        x: '700', y: '230', 'text-anchor': 'middle', 'font-size': '10'
    });
    wait2Text.textContent = 'Waiting Area';
    this.floorSvg.appendChild(wait2Text);

    // Beds & Patient Rooms - Clickable (Location 6)
    const bedsRect = this.createSVGElement('rect', {
        x: '780', y: '20', width: '190', height: '150',
        fill: '#f1f8e9', stroke: '#333'
    });
    bedsRect.style.cursor = 'pointer';
    bedsRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(6, 'Beds & Patient Rooms');
        }
    };
    this.floorSvg.appendChild(bedsRect);
    let roomsText = this.createSVGElement('text', {
        x: '875', y: '110', 'text-anchor': 'middle', 'font-size': '11'
    });
    roomsText.textContent = 'Beds & Patient Rooms';
    this.floorSvg.appendChild(roomsText);

    // Medical Surgery - Clickable (Location 8)
    const surgeryRect = this.createSVGElement('rect', {
        x: '780', y: '170', width: '190', height: '90',
        fill: '#f4ababff', stroke: '#333'
    });
    surgeryRect.style.cursor = 'pointer';
    surgeryRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(8, 'Medical Surgery');
        }
    };
    this.floorSvg.appendChild(surgeryRect);
    let surgeryText = this.createSVGElement('text', {
        x: '875', y: '220', 'text-anchor': 'middle', 'font-size': '9'
    });
    surgeryText.textContent = 'Medical Surgery';
    this.floorSvg.appendChild(surgeryText);

    // Storage Unit 1 - Non-clickable
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '630', y: '20', width: '65', height: '70',
        fill: '#cfd8dc', stroke: '#333'
    }));
    let storageText = this.createSVGElement('text', {
        x: '662', y: '60', 'text-anchor': 'middle', 'font-size': '9'
    });
    storageText.textContent = 'Storage';
    this.floorSvg.appendChild(storageText);

    // Storage Unit 2 - Non-clickable
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '706', y: '20', width: '65', height: '70',
        fill: '#cfd8dc', stroke: '#333'
    }));
    let storage2Text = this.createSVGElement('text', {
        x: '738', y: '60', 'text-anchor': 'middle', 'font-size': '9'
    });
    storage2Text.textContent = 'Storage';
    this.floorSvg.appendChild(storage2Text);
    
    // Operating Rooms (Wing 2) - Clickable (Location 8)
    const orRect = this.createSVGElement('rect', {
        x: '680', y: '320', width: '290', height: '150',
        fill: '#ffebee', stroke: '#333'
    });
    orRect.style.cursor = 'pointer';
    orRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(8, 'Operating Rooms');
        }
    };
    this.floorSvg.appendChild(orRect);
    let orText = this.createSVGElement('text', {
        x: '825', y: '400', 'text-anchor': 'middle', 'font-size': '11'
    });
    orText.textContent = 'Operating Rooms';
    this.floorSvg.appendChild(orText);

    // ICU - Clickable (Location 2)
    const icuRect = this.createSVGElement('rect', {
        x: '680', y: '480', width: '190', height: '100',
        fill: '#e1f5fe', stroke: '#333'
    });
    icuRect.style.cursor = 'pointer';
    icuRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(2, 'ICU');
        }
    };
    this.floorSvg.appendChild(icuRect);
    let icuText = this.createSVGElement('text', {
        x: '775', y: '530', 'text-anchor': 'middle', 'font-size': '11'
    });
    icuText.textContent = 'ICU';
    this.floorSvg.appendChild(icuText);

    // Emergency Department (ED) - Clickable (Location 1)
    const edRect = this.createSVGElement('rect', {
        x: '880', y: '480', width: '90', height: '100',
        fill: '#ffccbc', stroke: '#333'
    });
    edRect.style.cursor = 'pointer';
    edRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(1, 'Emergency Department');
        }
    };
    this.floorSvg.appendChild(edRect);
    let edText = this.createSVGElement('text', {
        x: '925', y: '530', 'text-anchor': 'middle', 'font-size': '11'
    });
    edText.textContent = 'Emergency Dept.';
    this.floorSvg.appendChild(edText);

    // Cafeteria - Clickable (Location 5)
    const cafeRect = this.createSVGElement('rect', {
        x: '20', y: '440', width: '200', height: '140',
        fill: '#f3e5f5', stroke: '#333'
    });
    cafeRect.style.cursor = 'pointer';
    cafeRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(5, 'Cafeteria');
        }
    };
    this.floorSvg.appendChild(cafeRect);
    let cafeText = this.createSVGElement('text', {
        x: '120', y: '520', 'text-anchor': 'middle', 'font-size': '11'
    });
    cafeText.textContent = 'Cafeteria';
    this.floorSvg.appendChild(cafeText);

    // Registration Desk - Clickable (could be Location 5)
    const regdeskRect = this.createSVGElement('rect', {
        x: '20', y: '255', width: '200', height: '80',
        fill: '#ede7f6', stroke: '#333'
    });
    regdeskRect.style.cursor = 'pointer';
    regdeskRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(5, 'Registration Desk');
        }
    };
    this.floorSvg.appendChild(regdeskRect);
    let regdeskText = this.createSVGElement('text', {
        x: '120', y: '300', 'text-anchor': 'middle', 'font-size': '11'
    });
    regdeskText.textContent = 'Registration Desk';
    this.floorSvg.appendChild(regdeskText);

    // Waiting Area - Clickable
    const waitingRect = this.createSVGElement('rect', {
        x: '20', y: '350', width: '200', height: '80',
        fill: '#ede7f6', stroke: '#333'
    });
    waitingRect.style.cursor = 'pointer';
    waitingRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(5, 'Waiting Area');
        }
    };
    this.floorSvg.appendChild(waitingRect);
    let waitingText = this.createSVGElement('text', {
        x: '120', y: '400', 'text-anchor': 'middle', 'font-size': '11'
    });
    waitingText.textContent = 'Waiting Area';
    this.floorSvg.appendChild(waitingText);

    // Entrance label
    const entranceText = this.createSVGElement('text', {
        x: '95', y: '210', 'text-anchor': 'middle', 'font-size': '15', 'font-weight': 'bold'
    });
    entranceText.textContent = 'ENTRANCE';
    this.floorSvg.appendChild(entranceText);

    // Emergency Entrance label
    const emerentranceText = this.createSVGElement('text', {
        x: '850', y: '300', 'text-anchor': 'middle', 'font-size': '15', 'font-weight': 'bold'
    });
    emerentranceText.textContent = 'EMERGENCY ENTRANCE';
    this.floorSvg.appendChild(emerentranceText);

    // Add drones to the map
    this.addDronesToSVG(1);
    }

    renderFloor2() {
    this.floorTitle.textContent = 'Floor 2 - Maternity & Specialized Care';
    
    // Outer border
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '10', y: '10', width: '980', height: '580',
        fill: '#fff', stroke: '#333', 'stroke-width': '2'
    }));

    // Mother-Baby Rooms - Clickable (Location 6)
    const momRect = this.createSVGElement('rect', {
        x: '20', y: '20', width: '150', height: '120',
        fill: '#ffe6f0', stroke: '#333'
    });
    momRect.style.cursor = 'pointer';
    momRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(6, 'Mother-Baby Rooms');
        }
    };
    this.floorSvg.appendChild(momRect);
    const momText1 = this.createSVGElement('text', {
        x: '95', y: '70', 'text-anchor': 'middle', 'font-size': '11'
    });
    momText1.textContent = 'Mother-Baby';
    this.floorSvg.appendChild(momText1);
    
    const momText2 = this.createSVGElement('text', {
        x: '95', y: '90', 'text-anchor': 'middle', 'font-size': '11'
    });
    momText2.textContent = 'Rooms';
    this.floorSvg.appendChild(momText2);

    // Lactation / Consulting - Clickable (Location 7)
    const consultRect = this.createSVGElement('rect', {
        x: '190', y: '20', width: '80', height: '120',
        fill: '#fce4ec', stroke: '#333'
    });
    consultRect.style.cursor = 'pointer';
    consultRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(7, 'Lactation / Consulting');
        }
    };
    this.floorSvg.appendChild(consultRect);
    let consultText = this.createSVGElement('text', {
        x: '230', y: '80', 'text-anchor': 'middle', 'font-size': '10'
    });
    consultText.textContent = 'Consulting';
    this.floorSvg.appendChild(consultText);

    // C-Section Birthing Suite - Clickable (Location 8)
    const csecRect = this.createSVGElement('rect', {
        x: '280', y: '20', width: '420', height: '120',
        fill: '#ffe0e0', stroke: '#333'
    });
    csecRect.style.cursor = 'pointer';
    csecRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(8, 'C-Section Birthing Suite');
        }
    };
    this.floorSvg.appendChild(csecRect);
    let csecText = this.createSVGElement('text', {
        x: '490', y: '85', 'text-anchor': 'middle', 'font-size': '12'
    });
    csecText.textContent = 'C-Section Birthing Suite';
    this.floorSvg.appendChild(csecText);

    // Orthopedics - Clickable (Location 4)
    const orthoRect = this.createSVGElement('rect', {
        x: '780', y: '20', width: '200', height: '120',
        fill: '#e3f2fd', stroke: '#333'
    });
    orthoRect.style.cursor = 'pointer';
    orthoRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(4, 'Orthopedics');
        }
    };
    this.floorSvg.appendChild(orthoRect);
    let orthoText = this.createSVGElement('text', {
        x: '880', y: '85', 'text-anchor': 'middle', 'font-size': '11'
    });
    orthoText.textContent = 'Orthopedics';
    this.floorSvg.appendChild(orthoText);

    // Women's Health Area - Clickable (Location 7)
    const womensRect = this.createSVGElement('rect', {
        x: '780', y: '150', width: '200', height: '80',
        fill: '#f8bbd0', stroke: '#333'
    });
    womensRect.style.cursor = 'pointer';
    womensRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(7, 'Women\'s Health');
        }
    };
    this.floorSvg.appendChild(womensRect);
    let womensText = this.createSVGElement('text', {
        x: '880', y: '195', 'text-anchor': 'middle', 'font-size': '10'
    });
    womensText.textContent = 'Women\'s Health';
    this.floorSvg.appendChild(womensText);

    // Quarantine Rooms - Clickable (Location 6)
    const quarantineRect = this.createSVGElement('rect', {
        x: '20', y: '200', width: '200', height: '370',
        fill: '#fff3e0', stroke: '#333'
    });
    quarantineRect.style.cursor = 'pointer';
    quarantineRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(6, 'Quarantine Rooms');
        }
    };
    this.floorSvg.appendChild(quarantineRect);
    let quarantineText = this.createSVGElement('text', {
        x: '120', y: '360', 'text-anchor': 'middle', 'font-size': '11'
    });
    quarantineText.textContent = 'Quarantine Rooms';
    this.floorSvg.appendChild(quarantineText);

    // Engineering Room / Energy - Non-clickable
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '230', y: '270', width: '220', height: '200',
        fill: '#e0f2f1', stroke: '#333'
    }));
    let engText = this.createSVGElement('text', {
        x: '340', y: '380', 'text-anchor': 'middle', 'font-size': '11'
    });
    engText.textContent = 'Engineering Room / Energy Room';
    this.floorSvg.appendChild(engText);

    // Biomedical Waste - Non-clickable
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '780', y: '250', width: '200', height: '100',
        fill: '#ef9a9a', stroke: '#333'
    }));
    let bioText = this.createSVGElement('text', {
        x: '880', y: '305', 'text-anchor': 'middle', 'font-size': '10'
    });
    bioText.textContent = 'Biomedical Waste';
    this.floorSvg.appendChild(bioText);

    // Storage Units - Non-clickable
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '780', y: '370', width: '200', height: '80',
        fill: '#cfd8dc', stroke: '#333'
    }));
    let storageText = this.createSVGElement('text', {
        x: '880', y: '415', 'text-anchor': 'middle', 'font-size': '10'
    });
    storageText.textContent = 'Storage Units';
    this.floorSvg.appendChild(storageText);

    // Housekeeping - Non-clickable
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '230', y: '485', width: '260', height: '80',
        fill: '#ede7f6', stroke: '#333'
    }));
    let houseText = this.createSVGElement('text', {
        x: '350', y: '530', 'text-anchor': 'middle', 'font-size': '11'
    });
    houseText.textContent = 'Housekeeping';
    this.floorSvg.appendChild(houseText);

    // Laundry - Clickable (Location 5)
    const laundryRect = this.createSVGElement('rect', {
        x: '500', y: '485', width: '160', height: '80',
        fill: '#f1f8e9', stroke: '#333'
    });
    laundryRect.style.cursor = 'pointer';
    laundryRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(5, 'Laundry');
        }
    };
    this.floorSvg.appendChild(laundryRect);
    let laundryText = this.createSVGElement('text', {
        x: '570', y: '530', 'text-anchor': 'middle', 'font-size': '11'
    });
    laundryText.textContent = 'Laundry';
    this.floorSvg.appendChild(laundryText);

    // Drone Storage - Clickable (for charging stations)
    const droneStorageRect = this.createSVGElement('rect', {
        x: '780', y: '470', width: '200', height: '100',
        fill: '#acceccff', stroke: '#333'
    });
    droneStorageRect.style.cursor = 'pointer';
    droneStorageRect.onclick = () => {
        if (window.onLocationSelected) {
            window.onLocationSelected(9, 'Drone Storage');
        }
    };
    this.floorSvg.appendChild(droneStorageRect);
    let dronestorageText = this.createSVGElement('text', {
        x: '880', y: '520', 'text-anchor': 'middle', 'font-size': '11'
    });
    dronestorageText.textContent = 'Drone Storage';
    this.floorSvg.appendChild(dronestorageText);

    // Elevator - Non-clickable
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '680', y: '485', width: '80', height: '80',
        fill: '#d4d4d4', stroke: '#333'
    }));
    const elevText = this.createSVGElement('text', {
        x: '720', y: '520', 'text-anchor': 'middle', 'font-size': '10'
    });
    elevText.textContent = 'Elevator';
    this.floorSvg.appendChild(elevText);

    // Stairs label
    const stairText = this.createSVGElement('text', {
        x: '100', y: '180', 'text-anchor': 'middle', 'font-size': '13', 'font-weight': 'bold'
    });
    stairText.textContent = 'STAIRS';
    this.floorSvg.appendChild(stairText);

    // Stairs label (upper right)
    const stairsText = this.createSVGElement('text', {
        x: '740', y: '80', 'text-anchor': 'middle', 'font-size': '15', 'font-weight': 'bold'
    });
    stairsText.textContent = 'STAIRS';
    this.floorSvg.appendChild(stairsText);

    // Add drones to the map
    this.addDronesToSVG(2);
    }

addDronesToSVG(floor) {
    const floorDrones = this.drones.filter(d => (d.floor || 1) === floor);
    
    floorDrones.forEach(drone => {
        // Calculate current position along route (stationary if not assigned)
        const currentPos = this.calculateDronePosition(drone);
        
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.style.cursor = 'pointer';
        g.style.pointerEvents = 'all'; // Ensure click events work
        // Store drone reference for click handler
        g.setAttribute('data-drone-id', drone.drone_id || drone.id);
        g.setAttribute('data-drone-index', floorDrones.indexOf(drone));
        
        // Create click handler that captures the drone
        // This only shows info - it does NOT affect drone movement or position
        const clickHandler = (e) => {
            e.stopPropagation(); // Prevent event bubbling to map click handler
            e.preventDefault(); // Prevent any default behavior
            // Show drone info without affecting movement
            this.showDroneInfo(drone);
        };
        g.addEventListener('click', clickHandler, { passive: false });
        
        // Determine color: red for emergency, blue for normal
        let droneColor = '#4ECDC4'; // Default blue
        if (drone.emergency_drone) {
            droneColor = drone.status === 'available' || drone.status === 'Available' ? '#FF0000' : '#FF6B6B'; // Bright red for emergency
        } else {
            droneColor = drone.status === 'available' || drone.status === 'Available' ? '#0066FF' : '#4ECDC4'; // Bright blue for normal
        }
        
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', currentPos.x);
        circle.setAttribute('cy', currentPos.y);
        circle.setAttribute('r', '12'); // Slightly larger for easier clicking
        circle.setAttribute('fill', droneColor);
        circle.setAttribute('stroke', '#000');
        circle.setAttribute('stroke-width', '2');
        circle.classList.add('drone-dot');
        circle.style.pointerEvents = 'all';
        circle.addEventListener('click', clickHandler, { passive: false });
        // Prevent hover/pointer events from affecting drone movement
        // Hover events should ONLY change cursor - they must NOT trigger any position calculations
        circle.addEventListener('mouseenter', (e) => {
            e.stopPropagation(); // Don't bubble to parent
            e.preventDefault(); // Prevent any default behavior
            // ONLY change cursor - do NOT trigger any position calculations or re-renders
            circle.style.cursor = 'pointer';
            // Explicitly prevent any position updates on hover
            return false;
        }, { passive: false, capture: true });
        circle.addEventListener('mouseleave', (e) => {
            e.stopPropagation();
            e.preventDefault();
            // ONLY change cursor - do NOT trigger any position calculations or re-renders
            circle.style.cursor = 'pointer';
            // Explicitly prevent any position updates on hover
            return false;
        }, { passive: false, capture: true });
        
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', currentPos.x);
        text.setAttribute('y', parseInt(currentPos.y) + 30);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', '11');
        text.setAttribute('font-weight', 'bold');
        text.setAttribute('fill', '#000');
        text.style.pointerEvents = 'none'; // Don't block clicks on text
        text.textContent = drone.id || `D${drone.drone_id || drone.id}`;
        
        g.appendChild(circle);
        g.appendChild(text);
        this.floorSvg.appendChild(g);
    });
}

// Update drone positions continuously for smooth animation
// Only update positions for drones in transit with assigned requests; others stay stationary
updateDronePositions() {
    let needsUpdate = false;
    
    this.drones.forEach(drone => {
        // Check if drone has an assigned request
        const hasRequest = drone.assigned_request_id !== undefined && drone.assigned_request_id !== null;
        const isInTransit = drone.status === 'assigned' || drone.status === 'Assigned' || 
                           drone.status === 'in_transit' || drone.status === 'In Transit';
        
        // Always use calculateDronePosition for consistent positioning logic
        // This ensures drones without requests stay stationary at placeholder positions
        const currentPos = this.calculateDronePosition(drone);
        
        // Only mark as needing update if drone is actually moving (has request and is in transit)
        if (isInTransit && hasRequest && drone.delivery_route && drone.delivery_route.length > 1) {
            // Drone is moving - update position
            drone.x = currentPos.x;
            drone.y = currentPos.y;
            needsUpdate = true;
        } else {
            // Drone is stationary - still update position to ensure correct placeholder placement
            // (positioned at placeholder location when no request)
            drone.x = currentPos.x;
            drone.y = currentPos.y;
            // Don't mark as needsUpdate since these don't change position over time
        }
    });
    
    // Only re-render if we have drones in transit that need updating
    if (needsUpdate && this.viewMode === '2d') {
        this.render2DFloor();
    }
}

showDroneInfo(drone) {
    this.selectedDrone = drone;
    document.getElementById('drone-name').textContent = drone.name || `Drone ${drone.id}`;
    document.getElementById('drone-id').textContent = drone.id;
    document.getElementById('drone-floor').textContent = drone.floor || 1;
    document.getElementById('drone-status').textContent = drone.status || 'Unknown';
    const locationName = drone.location_name || `Location ${drone.location_id || drone.current_location_id || 'N/A'}`;
    document.getElementById('drone-position').textContent = `${locationName} (${Math.round(drone.x || 0)}, ${Math.round(drone.y || 0)})`;
    
    // Update battery info if available
    const batteryEl = document.getElementById('drone-battery');
    if (batteryEl && drone.battery_percent !== undefined) {
        batteryEl.textContent = `${drone.battery_percent}% (${drone.battery_level_kwh || 0} kWh / ${drone.battery_capacity_kwh || 0.5} kWh)`;
    } else if (batteryEl) {
        batteryEl.textContent = 'N/A';
    }
    
    // Update payload info if available
    const payloadEl = document.getElementById('drone-payload');
    if (payloadEl) {
        payloadEl.textContent = drone.current_payload_weight_kg !== undefined ? `${drone.current_payload_weight_kg} kg` : '0 kg';
    }
    
    // Update speed info if available
    const speedEl = document.getElementById('drone-speed');
    if (speedEl) {
        speedEl.textContent = drone.current_speed_m_per_sec !== undefined ? `${drone.current_speed_m_per_sec} m/s` : 'N/A';
    }
    
    // Update route info if available
    const routeEl = document.getElementById('drone-route');
    if (routeEl) {
        if (drone.delivery_route && drone.delivery_route.length > 0) {
            routeEl.textContent = drone.delivery_route.join(' → ');
        } else {
            routeEl.textContent = 'None';
        }
    }
    
    // Display request info and energy/carbon data
    // This will be populated from the full drone data fetched from API
    this.droneInfo.style.display = 'block';
    
    // Fetch full drone data if we only have basic info
    if (drone.drone_id && !drone.request_info) {
        this.fetchDroneDetails(drone.drone_id);
    } else if (drone.request_info) {
        this.displayDroneRequestAndEnergy(drone);
    }
}

async fetchDroneDetails(droneId) {
    try {
        const response = await fetch(`${window.API_BASE_MAP || ''}/api/drones/all`);
        if (!response.ok) return;
        const data = await response.json();
        const fullDrone = data.drones.find(d => d.id === parseInt(droneId));
        if (fullDrone) {
            this.displayDroneRequestAndEnergy(fullDrone);
        }
    } catch (error) {
        console.error('Error fetching drone details:', error);
    }
}

    // Calculate current position along route based on elapsed time and speed
    // Drones are stationary at their location until assigned a request, then they move along route
    calculateDronePosition(drone) {
        // Check if drone has an assigned request
        // Drones without requests stay completely stationary at their current location
        const hasRequest = drone.assigned_request_id !== undefined && drone.assigned_request_id !== null;
        
        // Only calculate movement if drone is actively in transit (assigned or in_transit) AND has a request
        const isInTransit = drone.status === 'assigned' || drone.status === 'Assigned' || 
                           drone.status === 'in_transit' || drone.status === 'In Transit';
        
        // If drone has a route, is in transit, AND has an assigned request, calculate position along route
        // Otherwise, drone stays stationary at its current location
        if (drone.delivery_route && drone.delivery_route.length > 1 && isInTransit && hasRequest) {
            
            const droneId = drone.drone_id || drone.id;
            
            // Initialize or update flight tracking
            if (!this.droneFlights[droneId]) {
                // Initialize flight tracking
                const speed = drone.current_speed_m_per_sec || 2.5; // m/s
                const startTime = drone.flight_start_time ? 
                    new Date(drone.flight_start_time).getTime() : Date.now();
                this.droneFlights[droneId] = {
                    route: drone.delivery_route,
                    startTime: startTime,
                    speed: speed,
                    is_emergency: drone.emergency_drone || false
                };
            } else {
                // Update flight info with backend data
                if (drone.flight_start_time) {
                    this.droneFlights[droneId].startTime = new Date(drone.flight_start_time).getTime();
                }
                if (drone.current_speed_m_per_sec) {
                    this.droneFlights[droneId].speed = drone.current_speed_m_per_sec;
                }
                // Update emergency flag for lane positioning
                if (drone.emergency_drone !== undefined) {
                    this.droneFlights[droneId].is_emergency = drone.emergency_drone || false;
                }
                if (drone.delivery_route) {
                    // Only update route if it changed (for multi-stop deliveries)
                    if (JSON.stringify(this.droneFlights[droneId].route) !== JSON.stringify(drone.delivery_route)) {
                        this.droneFlights[droneId].route = drone.delivery_route;
                        // Reset start time for new route
                        if (drone.flight_start_time) {
                            this.droneFlights[droneId].startTime = new Date(drone.flight_start_time).getTime();
                        } else {
                            this.droneFlights[droneId].startTime = Date.now();
                        }
                    }
                }
            }
            
            const flightData = this.droneFlights[droneId];
            const elapsedSeconds = (Date.now() - flightData.startTime) / 1000;
            const speed = flightData.speed; // m/s
            
            // Get LOCATION_TO_COORDS from prototype or window
            const LOCATION_TO_COORDS = this.LOCATION_TO_COORDS || window.LOCATION_TO_COORDS || {};
            
            // Convert route location IDs to coordinates
            const routeCoords = flightData.route.map(locId => {
                const loc = LOCATION_TO_COORDS[locId];
                if (loc) {
                    return { x: loc.realX !== undefined ? loc.realX : (loc.x || 0), y: loc.realY !== undefined ? loc.realY : (loc.y || 0), id: locId };
                }
                return null;
            }).filter(c => c !== null);
            
            if (routeCoords.length === 0) {
                // Fallback to current location
                const LOCATION_TO_COORDS = this.LOCATION_TO_COORDS || window.LOCATION_TO_COORDS || {};
                const loc = LOCATION_TO_COORDS[drone.current_location_id];
                return { x: loc ? (loc.x || 0) : 0, y: loc ? (loc.y || 0) : 0 };
            }
            
            // Calculate total distance along route
            // Pixel-to-meter conversion: realX/realY coordinates use units where 1 unit = 10 meters
            // Map display: realX 0-30 -> mapX 100-700 (600 pixels), realY 0-10 -> mapY 100-450 (350 pixels)
            // This means: 1 realX unit = 10m = 20 pixels (600/30), 1 realY unit = 10m = 35 pixels (350/10)
            // For distance calculation: realX/realY units are already in graph coordinates where 1 unit = 10m
            let totalDistance = 0;
            const segmentDistances = [];
            for (let i = 0; i < routeCoords.length - 1; i++) {
                const dx = routeCoords[i + 1].x - routeCoords[i].x;
                const dy = routeCoords[i + 1].y - routeCoords[i].y;
                // Distance in realX/realY units, where 1 unit = 10 meters (from graph.py)
                const distInUnits = Math.sqrt(dx * dx + dy * dy);
                // Convert to meters: each unit represents 10 meters
                const dist = distInUnits * 10; // meters
                segmentDistances.push(dist);
                totalDistance += dist;
            }
            
            // Calculate how far we've traveled
            // Speed is in m/s (from backend: EMERGENCY_SPEED_M_PER_SEC = 4.0, NORMAL_SPEED_M_PER_SEC = 2.5, etc.)
            const distanceTraveled = elapsedSeconds * speed; // meters
            
            if (distanceTraveled >= totalDistance) {
                // Reached destination
                const LOCATION_TO_COORDS = this.LOCATION_TO_COORDS || window.LOCATION_TO_COORDS || {};
                const finalLoc = routeCoords[routeCoords.length - 1];
                const mapLoc = LOCATION_TO_COORDS[finalLoc.id];
                // At destination, apply lane positioning based on drone type
                const isEmergency = drone.emergency_drone || drone.is_emergency || false;
                // For destination, just use the location center (no lane offset needed at stops)
                return { x: mapLoc ? mapLoc.x : finalLoc.x * 15, y: mapLoc ? mapLoc.y : finalLoc.y * 30 };
            }
            
            // Find which segment we're in
            let accumulatedDistance = 0;
            for (let i = 0; i < segmentDistances.length; i++) {
                if (distanceTraveled <= accumulatedDistance + segmentDistances[i]) {
                    // We're in this segment
                    const segmentProgress = (distanceTraveled - accumulatedDistance) / segmentDistances[i];
                    const startCoord = routeCoords[i];
                    const endCoord = routeCoords[i + 1];
                    
                    // Interpolate between start and end (center of path)
                    const realX = startCoord.x + (endCoord.x - startCoord.x) * segmentProgress;
                    const realY = startCoord.y + (endCoord.y - startCoord.y) * segmentProgress;
                    
                    // 3-lane traffic system: drones stay in designated lanes
                    // Normal drones: stick to wall on their right (right lane)
                    // Emergency/ICU drones: use middle lane
                    // Check multiple possible sources for emergency drone flag
                    const isEmergency = drone.emergency_drone === true || 
                                       drone.is_emergency === true || 
                                       drone.emergency === true ||
                                       (flightData && flightData.is_emergency === true) ||
                                       false;
                    
                    // Calculate direction vector of this segment
                    const segmentDx = endCoord.x - startCoord.x;
                    const segmentDy = endCoord.y - startCoord.y;
                    const segmentLength = Math.sqrt(segmentDx * segmentDx + segmentDy * segmentDy);
                    
                    if (segmentLength > 0.001) { // Avoid division by zero
                        // Perpendicular vector pointing to the right (relative to travel direction)
                        // For direction (dx, dy), the right perpendicular is (-dy, dx)
                        const perpX = -segmentDy / segmentLength; // Normalized perpendicular X
                        const perpY = segmentDx / segmentLength;  // Normalized perpendicular Y
                        
                        // Lane offset in real coordinates (where 1 unit = 10 meters)
                        // Right lane offset: 1.0 units = 10 meters to the right (for normal drones)
                        // Middle lane: no offset (for emergency drones)
                        let laneOffset = 0;
                        if (!isEmergency) {
                            // Normal drones: offset to the right by ~1.5 meters (0.15 units)
                            // This makes them stick to the right wall
                            laneOffset = 0.15; // 1.5 meters to the right
                        } else {
                            // Emergency/ICU drones: stay in middle lane (no offset)
                            laneOffset = 0;
                        }
                        
                        // Apply perpendicular offset for lane positioning
                        const offsetX = perpX * laneOffset;
                        const offsetY = perpY * laneOffset;
                        
                        // Add lane offset to position
                        const realXWithLane = realX + offsetX;
                        const realYWithLane = realY + offsetY;
                        
                        // Convert real coordinates to map coordinates
                        // Map scaling: realX 0-30 -> mapX 100-700, realY 0-10 -> mapY 100-450
                        const mapX = 100 + (realXWithLane / 30) * 600;
                        const mapY = 100 + (realYWithLane / 10) * 350;
                        
                        return { x: mapX, y: mapY };
                    } else {
                        // Very short segment or zero-length: just use center position
                        const mapX = 100 + (realX / 30) * 600;
                        const mapY = 100 + (realY / 10) * 350;
                        return { x: mapX, y: mapY };
                    }
                }
                accumulatedDistance += segmentDistances[i];
            }
        }
        
        // Not in transit or no request - drone is completely stationary at its current location
        // Position drones at their assigned location (placeholders when no request)
        const LOCATION_TO_COORDS = this.LOCATION_TO_COORDS || window.LOCATION_TO_COORDS || {};
        const loc = LOCATION_TO_COORDS[drone.current_location_id];
        
        if (loc) {
            // For available drones (no request), position them at placeholder location
            // Offset slightly to the right and above room center to appear "parked"
            if (drone.status === 'available' || drone.status === 'Available' || !hasRequest) {
                // Placeholder position: offset by ~30 pixels right and ~20 pixels up from room center
                // This makes them appear "parked" outside the room when not assigned
                return { 
                    x: (loc.x || 0) + 30, 
                    y: (loc.y || 0) - 20 
                };
            }
            
            // For other statuses (completed, charging, etc.), use exact location
            // Charging stations are in LOCATION_TO_COORDS (locations 9-18), drones will navigate to them via routes
            return { x: loc.x || 0, y: loc.y || 0 };
        }
        
        // Fallback to stored position or default (shouldn't happen if location exists)
        return { x: drone.x || 0, y: drone.y || 0 };
    }
    
    displayDroneRequestAndEnergy(drone) {
    // Display request info
    const requestInfoHtml = drone.request_info ? `
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">
            <h5 style="margin-bottom: 10px; color: #667eea;">📦 Current Request</h5>
            <p><strong>Request ID:</strong> ${drone.request_info.id}</p>
            <p><strong>Priority:</strong> ${drone.request_info.priority_display}</p>
            <p><strong>Description:</strong> ${drone.request_info.description || 'N/A'}</p>
            <p><strong>Requester:</strong> ${drone.request_info.requester_name}</p>
            <p><strong>Destination:</strong> ${drone.request_info.destination_location_name}</p>
            <p><strong>Payload:</strong> ${drone.request_info.payload_weight_kg || 0} kg</p>
            <p><strong>Status:</strong> ${drone.request_info.status}</p>
        </div>
    ` : `
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">
            <p><em>No active request</em></p>
        </div>
    `;
    
    // Display energy/carbon data
    const energyInfoHtml = `
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">
            <h5 style="margin-bottom: 10px; color: #667eea;">⚡ Energy & Carbon Savings</h5>
            <p><strong>Energy Saved (This Request):</strong> ${drone.current_energy_saved_kwh || 0} kWh</p>
            <p><strong>CO₂ Saved (This Request):</strong> ${drone.current_carbon_saved_kg || 0} kg</p>
        </div>
    `;
    
    // Append to drone info (if elements exist)
    const droneInfoDiv = document.getElementById('drone-info');
    if (droneInfoDiv) {
        // Remove old request/energy sections if they exist
        const oldRequestDiv = droneInfoDiv.querySelector('.drone-request-info');
        const oldEnergyDiv = droneInfoDiv.querySelector('.drone-energy-info');
        if (oldRequestDiv) oldRequestDiv.remove();
        if (oldEnergyDiv) oldEnergyDiv.remove();
        
        // Add new sections
        const requestDiv = document.createElement('div');
        requestDiv.className = 'drone-request-info';
        requestDiv.innerHTML = requestInfoHtml;
        droneInfoDiv.appendChild(requestDiv);
        
        const energyDiv = document.createElement('div');
        energyDiv.className = 'drone-energy-info';
        energyDiv.innerHTML = energyInfoHtml;
        droneInfoDiv.appendChild(energyDiv);
    }
}

startDroneSimulation() {
    // Simulate real-time drone movement
    // REPLACE THIS WITH YOUR BACKEND API CALLS
    setInterval(() => {
        this.drones = this.drones.map(drone => ({
            ...drone,
            x: Math.max(20, Math.min(980, drone.x + (Math.random() - 0.5) * 20)),
            y: Math.max(20, Math.min(580, drone.y + (Math.random() - 0.5) * 20)),
        }));
        
        // Update 2D view if active
        if (this.viewMode === '2d') {
            this.render2DFloor();
        }
    }, 1000);
}

// METHOD TO CONNECT TO YOUR BACKEND
// Replace startDroneSimulation() with this when you're ready
async fetchDroneDataFromBackend() {
    try {
        const response = await fetch('YOUR_BACKEND_API_URL/drones');
        const data = await response.json();
        this.drones = data;
        
        // Update views
        if (this.viewMode === '3d') {
            this.updateDroneMeshes();
        } else {
            this.render2DFloor();
        }
    } catch (error) {
        console.error('Error fetching drone data:', error);
    }
}

// Call this method periodically to get real-time updates
startBackendPolling(intervalMs = 1000) {
    setInterval(() => {
        this.fetchDroneDataFromBackend();
    }, intervalMs);
}
}

const tracker = new HospitalDroneTracker();