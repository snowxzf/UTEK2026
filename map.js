//size of each floor: 1000 (wide) x 600 (tall) pixels

class HospitalDroneTracker {
    constructor() {
        this.viewMode = '3d'; 
        this.selectedFloor = null; 
        this.selectedDrone = null;
        
        // fake drone data to show it working 
        this.drones = [
            { id: 'D1', floor: 1, x: 200, y: 150, color: '#FF6B6B', name: 'Delivery Drone 1', status: 'Active' },
            { id: 'D2', floor: 1, x: 600, y: 300, color: '#4ECDC4', name: 'MedicSal Supply Drone', status: 'Active' },
            { id: 'D3', floor: 2, x: 400, y: 200, color: '#95E1D3', name: 'Emergency Drone', status: 'Standby' },
            { id: 'D4', floor: 1, x: 800, y: 400, color: '#FFE66D', name: 'Lab Sample Drone', status: 'Active' },
        ];

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

        this.init();
    }

    init() {
        this.setupControls();
        this.init3DView();
        this.startDroneSimulation();
        this.setupEventListeners();
    }

    setupControls() {
        this.updateControls();
    }

    updateControls() {
        this.controlsContainer.innerHTML = '';
        
        if (this.viewMode === '2d') {
            // Back to 3D button
            const backBtn = document.createElement('button');
            backBtn.className = 'tracker-button';
            backBtn.textContent = 'Back to 3D View';
            backBtn.onclick = () => this.switchTo3DView();
            this.controlsContainer.appendChild(backBtn);

            // Floor 1 button
            const floor1Btn = document.createElement('button');
            floor1Btn.className = `tracker-button ${this.selectedFloor === 1 ? 'active' : ''}`;
            floor1Btn.textContent = 'Floor 1';
            floor1Btn.onclick = () => this.switchFloor(1);
            this.controlsContainer.appendChild(floor1Btn);

            // Floor 2 button
            const floor2Btn = document.createElement('button');
            floor2Btn.className = `tracker-button ${this.selectedFloor === 2 ? 'active' : ''}`;
            floor2Btn.textContent = 'Floor 2';
            floor2Btn.onclick = () => this.switchFloor(2);
            this.controlsContainer.appendChild(floor2Btn);
        }
    }

    init3DView() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);

        this.camera = new THREE.PerspectiveCamera(
            75,
            this.canvas.clientWidth / this.canvas.clientHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 15, 20);
        this.camera.lookAt(0, 0, 0);

        this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true });
        this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);

        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true; // Smooth camera movement
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 10; // Minimum zoom
        this.controls.maxDistance = 50; // Maximum zoom
        this.controls.maxPolarAngle = Math.PI / 2; // Prevent going below ground

        //lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 20, 10);
        this.scene.add(directionalLight);

        //Floor 1
        const floor1Geometry = new THREE.BoxGeometry(20, 0.5, 12);
        const floor1Material = new THREE.MeshPhongMaterial({ color: 0x3498db });
        const floor1 = new THREE.Mesh(floor1Geometry, floor1Material);
        floor1.position.y = 0;
        floor1.userData = { floor: 1, clickable: true };
        this.scene.add(floor1);

        // Floor 1 edges
        const floor1Edge = new THREE.EdgesGeometry(floor1Geometry);
        const floor1Line = new THREE.LineSegments(floor1Edge, new THREE.LineBasicMaterial({ color: 0x000000 }));
        floor1Line.position.y = 0;
        this.scene.add(floor1Line);

        //Floor 2
        const floor2Geometry = new THREE.BoxGeometry(20, 0.5, 12);
        const floor2Material = new THREE.MeshPhongMaterial({ color: 0x2ecc71 });
        const floor2 = new THREE.Mesh(floor2Geometry, floor2Material);
        floor2.position.y = 6;
        floor2.userData = { floor: 2, clickable: true };
        this.scene.add(floor2);

        const floor2Edge = new THREE.EdgesGeometry(floor2Geometry);
        const floor2Line = new THREE.LineSegments(floor2Edge, new THREE.LineBasicMaterial({ color: 0x000000 }));
        floor2Line.position.y = 6;
        this.scene.add(floor2Line);

        this.updateDroneMeshes();

        this.animate();
    }

    updateDroneMeshes() {
        this.droneMeshes.forEach(mesh => this.scene.remove(mesh));
        this.droneMeshes = [];

        this.drones.forEach(drone => {
            const geometry = new THREE.SphereGeometry(0.3, 16, 16);
            const material = new THREE.MeshPhongMaterial({ color: drone.color });
            const sphere = new THREE.Mesh(geometry, material);
            const yPos = drone.floor === 1 ? 0.5 : 6.5;
            sphere.position.set((drone.x / 50) - 10, yPos, (drone.y / 50) - 6);
            sphere.userData = { droneId: drone.id };
            this.scene.add(sphere);
            this.droneMeshes.push(sphere);
        });
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        this.controls.update();

        // Update drone positions in 3D
        this.drones.forEach((drone, index) => {
            if (this.droneMeshes[index]) {
                const yPos = drone.floor === 1 ? 0.5 : 6.5;
                this.droneMeshes[index].position.set(
                    (drone.x / 50) - 10,
                    yPos,
                    (drone.y / 50) - 6
                );
            }
        });

        this.renderer.render(this.scene, this.camera);
    }

    setupEventListeners() {
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
        const intersects = raycaster.intersectObjects(this.scene.children);

        if (intersects.length > 0) {
            const obj = intersects[0].object;
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
            this.controls.update();
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

    // Pharmacy
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '20', y: '20', width: '150', height: '120',
        fill: '#e8f4f8', stroke: '#333'
    }));
    const pharmacyText = this.createSVGElement('text', {
        x: '95', y: '80', 'text-anchor': 'middle', 'font-size': '12'
    });
    pharmacyText.textContent = 'Pharmacy';
    this.floorSvg.appendChild(pharmacyText);

    // Stairs
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '180', y: '20', width: '50', height: '80',
        fill: '#d4d4d4', stroke: '#333'
    }));
    const stairsText = this.createSVGElement('text', {
        x: '205', y: '65', 'text-anchor': 'middle', 'font-size': '10'
    });
    stairsText.textContent = 'Stairs';
    this.floorSvg.appendChild(stairsText);

    // Elevator
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '240', y: '20', width: '50', height: '80',
        fill: '#d4d4d4', stroke: '#333'
    }));
    const elevText = this.createSVGElement('text', {
        x: '265', y: '60', 'text-anchor': 'middle', 'font-size': '10'
    });
    elevText.textContent = 'Elevator';
    this.floorSvg.appendChild(elevText);

    // Imaging (Radiology / CT / X-ray)
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '180', y: '20', width: '120', height: '120',
        fill: '#e3f2fd', stroke: '#333'
    }));
    let imagingText = this.createSVGElement('text', {
        x: '240', y: '85', 'text-anchor': 'middle', 'font-size': '11'
    });
    imagingText.textContent = 'Imaging';
    this.floorSvg.appendChild(imagingText);

    // Lab rooms: sexology, neurology,etc. 
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '310', y: '480', width: '360', height: '100',
        fill: '#e8f5e9', stroke: '#333'
    }));
    let labText = this.createSVGElement('text', {
        x: '450', y: '540', 'text-anchor': 'middle', 'font-size': '10'
    });
    labText.textContent = 'Specialized Lab Rooms';
    this.floorSvg.appendChild(labText);

    //Drone storage
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '230', y: '480', width: '70', height: '100',
        fill: '#acceccff', stroke: '#333'
    }));
    let dronestorageText = this.createSVGElement('text', {
        x: '266', y: '530', 'text-anchor': 'middle', 'font-size': '10'
    });
    dronestorageText.textContent = 'Drone Storeage';
    this.floorSvg.appendChild(dronestorageText);

    // General Ward
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '310', y: '20', width: '300', height: '120',
        fill: '#fffde7', stroke: '#333'
    }));
    let generalText = this.createSVGElement('text', {
        x: '460', y: '85', 'text-anchor': 'middle', 'font-size': '11'
    });
    generalText.textContent = 'General Ward';
    this.floorSvg.appendChild(generalText);

    // diagonistic room
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '310', y: '150', width: '300', height: '90',
        fill: '#fce4ec', stroke: '#333'
    }));
    let diagText = this.createSVGElement('text', {
        x: '460', y: '205', 'text-anchor': 'middle', 'font-size': '11'
    });
    diagText.textContent = 'Diagonistic Rooms';
    this.floorSvg.appendChild(diagText);

    // Occupational Therapy Area
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '630', y: '100', width: '140', height: '90',
        fill: '#ede7f6', stroke: '#333'
    }));
    let otText = this.createSVGElement('text', {
        x: '700', y: '150', 'text-anchor': 'middle', 'font-size': '10'
    });
    otText.textContent = 'Occupational Therapy';
    this.floorSvg.appendChild(otText);

    // Waiting rm pt2
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '630', y: '200', width: '140', height: '60',
        fill: '#ede7f6', stroke: '#333'
    }));
    let wait2Text = this.createSVGElement('text', {
        x: '700', y: '230', 'text-anchor': 'middle', 'font-size': '10'
    });
    wait2Text.textContent = 'Waiting Area';
    this.floorSvg.appendChild(wait2Text);

    // Medical Surgey 
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '780', y: '20', width: '190', height: '150',
        fill: '#f1f8e9', stroke: '#333'
    }));
    let roomsText = this.createSVGElement('text', {
        x: '875', y: '110', 'text-anchor': 'middle', 'font-size': '11'
    });
    roomsText.textContent = 'Beds & Patient Rooms';
    this.floorSvg.appendChild(roomsText);

    // Medical Surgery
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '780', y: '170', width: '190', height: '90',
        fill: '#f4ababff', stroke: '#333'
    }));
    let surgeryText = this.createSVGElement('text', {
        x: '875', y: '220', 'text-anchor': 'middle', 'font-size': '9'
    });
    surgeryText.textContent = 'Medical Surgery';
    this.floorSvg.appendChild(surgeryText);

    // Storage Unit 1
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '630', y: '20', width: '65', height: '70',
        fill: '#cfd8dc', stroke: '#333'
    }));
    let storageText = this.createSVGElement('text', {
        x: '660', y: '60', 'text-anchor': 'middle', 'font-size': '9'
    });
    storageText.textContent = 'Storage';
    this.floorSvg.appendChild(storageText);

    // Storage Unit 2
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '706', y: '20', width: '65', height: '70',
        fill: '#cfd8dc', stroke: '#333'
    }));
    let storage2Text = this.createSVGElement('text', {
        x: '740', y: '60', 'text-anchor': 'middle', 'font-size': '9'
    });
    storage2Text.textContent = 'Storage';
    this.floorSvg.appendChild(storage2Text);
    
    // Operating Rooms (Wing 2)
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '680', y: '320', width: '290', height: '150',
        fill: '#ffebee', stroke: '#333'
    }));
    let orText = this.createSVGElement('text', {
        x: '825', y: '400', 'text-anchor': 'middle', 'font-size': '11'
    });
    orText.textContent = 'Operating Rooms';
    this.floorSvg.appendChild(orText);

    // ICU
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '680', y: '480', width: '190', height: '100',
        fill: '#e1f5fe', stroke: '#333'
    }));
    let icuText = this.createSVGElement('text', {
        x: '775', y: '530', 'text-anchor': 'middle', 'font-size': '11'
    });
    icuText.textContent = 'ICU';
    this.floorSvg.appendChild(icuText);

    // Emergency Department (ED)
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '880', y: '480', width: '90', height: '100',
        fill: '#ffccbc', stroke: '#333'
    }));
    let edText = this.createSVGElement('text', {
        x: '925', y: '530', 'text-anchor': 'middle', 'font-size': '11'
    });
    edText.textContent = 'Emergency Dept.';
    this.floorSvg.appendChild(edText);

    // Cafeteria 
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '20', y: '440', width: '200', height: '140',
        fill: '#f3e5f5', stroke: '#333'
    }));
    let cafeText = this.createSVGElement('text', {
        x: '120', y: '520', 'text-anchor': 'middle', 'font-size': '11'
    });
    cafeText.textContent = 'Cafeteria';
    this.floorSvg.appendChild(cafeText);

    // Registration desk 
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '20', y: '255', width: '200', height: '80',
        fill: '#ede7f6', stroke: '#333'
    }));
    let regdeskText = this.createSVGElement('text', {
        x: '120', y: '300', 'text-anchor': 'middle', 'font-size': '11'
    });
    regdeskText.textContent = 'Registration Desk';
    this.floorSvg.appendChild(regdeskText);

    //Waiting area
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '20', y: '350', width: '200', height: '80',
        fill: '#ede7f6', stroke: '#333'
    }));
    let waitingText = this.createSVGElement('text', {
        x: '120', y: '400', 'text-anchor': 'middle', 'font-size': '11'
    });
    waitingText.textContent = 'Waiting Area';
    this.floorSvg.appendChild(waitingText);

    //extra text stuff here 
    const entranceText = this.createSVGElement('text', {
    x: '95',
    y: '210',
    'text-anchor': 'middle',
    'font-size': '15',
    'font-weight': 'bold'
    });
    entranceText.textContent = 'ENTRANCE';
    this.floorSvg.appendChild(entranceText);

    //extra text stuff here 
    const emerentranceText = this.createSVGElement('text', {
    x: '850',
    y: '300',
    'text-anchor': 'middle',
    'font-size': '15',
    'font-weight': 'bold'
    });
    emerentranceText.textContent = 'EMERGENCY ENTRANCE';
    this.floorSvg.appendChild(emerentranceText);


    this.addDronesToSVG(1);
    }

    renderFloor2() {
    this.floorTitle.textContent = 'Floor 2 - Maternity & Specialized Care';
    
    // Outer border
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '10', y: '10', width: '980', height: '580',
        fill: '#fff', stroke: '#333', 'stroke-width': '2'
    }));

    // Mother-Baby Rooms
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '20', y: '20', width: '150', height: '120',
        fill: '#ffe6f0', stroke: '#333'
    }));
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

    // Lactation / Consulting
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '190', y: '20', width: '80', height: '120',
        fill: '#fce4ec', stroke: '#333'
    }));
    let consultText = this.createSVGElement('text', {
        x: '230', y: '80', 'text-anchor': 'middle', 'font-size': '10'
    });
    consultText.textContent = 'Consulting';
    this.floorSvg.appendChild(consultText);

    // C-Section Birthing Suite
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '280', y: '20', width: '420', height: '120',
        fill: '#ffe0e0', stroke: '#333'
    }));
    let csecText = this.createSVGElement('text', {
        x: '490', y: '85', 'text-anchor': 'middle', 'font-size': '12'
    });
    csecText.textContent = 'C-Section Birthing Suite';
    this.floorSvg.appendChild(csecText);

    // Orthopedics
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '780', y: '20', width: '200', height: '120',
        fill: '#e3f2fd', stroke: '#333'
    }));
    let orthoText = this.createSVGElement('text', {
        x: '890', y: '85', 'text-anchor': 'middle', 'font-size': '11'
    });
    orthoText.textContent = 'Orthopedics';
    this.floorSvg.appendChild(orthoText);

    // Women’s Health Area
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '780', y: '150', width: '200', height: '80',
        fill: '#f8bbd0', stroke: '#333'
    }));
    let womensText = this.createSVGElement('text', {
        x: '880', y: '195', 'text-anchor': 'middle', 'font-size': '10'
    });
    womensText.textContent = 'Women’s Health';
    this.floorSvg.appendChild(womensText);

    // Quarantine Rooms
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '20', y: '200', width: '200', height: '370',
        fill: '#fff3e0', stroke: '#333'
    }));
    let quarantineText = this.createSVGElement('text', {
        x: '120', y: '360', 'text-anchor': 'middle', 'font-size': '11'
    });
    quarantineText.textContent = 'Quarantine Rooms';
    this.floorSvg.appendChild(quarantineText);

    // Engineering Room / Energy
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '230', y: '270', width: '220', height: '200',
        fill: '#e0f2f1', stroke: '#333'
    }));
    let engText = this.createSVGElement('text', {
        x: '335', y: '380', 'text-anchor': 'middle', 'font-size': '11'
    });
    engText.textContent = 'Engineering Room / Energy Room';
    this.floorSvg.appendChild(engText);

    // Biomedical Waste
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '780', y: '250', width: '200', height: '100',
        fill: '#ef9a9a', stroke: '#333'
    }));
    let bioText = this.createSVGElement('text', {
        x: '880', y: '305', 'text-anchor': 'middle', 'font-size': '10'
    });
    bioText.textContent = 'Biomedical Waste';
    this.floorSvg.appendChild(bioText);

    // Storage Units
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '780', y: '370', width: '200', height: '80',
        fill: '#cfd8dc', stroke: '#333'
    }));
    let storageText = this.createSVGElement('text', {
        x: '880', y: '415', 'text-anchor': 'middle', 'font-size': '10'
    });
    storageText.textContent = 'Storage Units';
    this.floorSvg.appendChild(storageText);

    // Housekeeping
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '230', y: '485', width: '260', height: '80',
        fill: '#ede7f6', stroke: '#333'
    }));
    let houseText = this.createSVGElement('text', {
        x: '350', y: '530', 'text-anchor': 'middle', 'font-size': '11'
    });
    houseText.textContent = 'Housekeeping';
    this.floorSvg.appendChild(houseText);

    // Laundry
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '500', y: '485', width: '160', height: '80',
        fill: '#f1f8e9', stroke: '#333'
    }));
    let laundryText = this.createSVGElement('text', {
        x: '570', y: '530', 'text-anchor': 'middle', 'font-size': '11'
    });
    laundryText.textContent = 'Laundry';
    this.floorSvg.appendChild(laundryText);

    //Drone storage
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '780', y: '470', width: '200', height: '100',
        fill: '#acceccff', stroke: '#333'
    }));
    let dronestorageText = this.createSVGElement('text', {
        x: '880', y: '520', 'text-anchor': 'middle', 'font-size': '11'
    });
    dronestorageText.textContent = 'Drone Storage';
    this.floorSvg.appendChild(dronestorageText);

    // Elevator
    this.floorSvg.appendChild(this.createSVGElement('rect', {
        x: '680', y: '485', width: '80', height: '80',
        fill: '#d4d4d4', stroke: '#333'
    }));
    const elevText = this.createSVGElement('text', {
        x: '720', y: '520', 'text-anchor': 'middle', 'font-size': '10'
    });
    elevText.textContent = 'Elevator';
    this.floorSvg.appendChild(elevText);

    //extra text stuff here 
    const stairText = this.createSVGElement('text', {
    x: '100',
    y: '180',
    'text-anchor': 'middle',
    'font-size': '13',
    'font-weight': 'bold'
    });
    stairText.textContent = 'STAIRS';
    this.floorSvg.appendChild(stairText);

    const stairsText = this.createSVGElement('text', {
    x: '740',
    y: '80',
    'text-anchor': 'middle',
    'font-size': '15',
    'font-weight': 'bold'
    });
    stairsText.textContent = 'STAIRS';
    this.floorSvg.appendChild(stairsText);

    this.addDronesToSVG(2);
    }

addDronesToSVG(floor) {
    const floorDrones = this.drones.filter(d => d.floor === floor);
    
    floorDrones.forEach(drone => {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.style.cursor = 'pointer';
        g.onclick = () => this.showDroneInfo(drone);
        
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', drone.x);
        circle.setAttribute('cy', drone.y);
        circle.setAttribute('r', '8');
        circle.setAttribute('fill', drone.color);
        circle.setAttribute('stroke', '#000');
        circle.setAttribute('stroke-width', '2');
        circle.classList.add('drone-dot');
        
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', drone.x);
        text.setAttribute('y', parseInt(drone.y) + 25);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', '10');
        text.setAttribute('font-weight', 'bold');
        text.textContent = drone.id;
        
        g.appendChild(circle);
        g.appendChild(text);
        this.floorSvg.appendChild(g);
    });
}

showDroneInfo(drone) {
    this.selectedDrone = drone;
    document.getElementById('drone-name').textContent = drone.name;
    document.getElementById('drone-id').textContent = drone.id;
    document.getElementById('drone-floor').textContent = drone.floor;
    document.getElementById('drone-status').textContent = drone.status;
    document.getElementById('drone-position').textContent = `(${Math.round(drone.x)}, ${Math.round(drone.y)})`;
    this.droneInfo.style.display = 'block';
}

startDroneSimulation() {
    // Simulate drone movement
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

startBackendPolling(intervalMs = 1000) {
    setInterval(() => {
        this.fetchDroneDataFromBackend();
    }, intervalMs);
}
}

const tracker = new HospitalDroneTracker();