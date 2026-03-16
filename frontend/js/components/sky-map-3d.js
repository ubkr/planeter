/**
 * sky-map-3d.js - Immersive 3D sky-dome viewer using Three.js.
 *
 * Renders a WebGL hemisphere scene with:
 *   - A dark celestial sphere (inside-out, camera at origin)
 *   - A flat horizon ground plane
 *   - An alt-azimuth grid (altitude rings at 0°/30°/60°, azimuth lines every 45°)
 *   - Cardinal direction labels (N, O, S, V) rendered as canvas-texture sprites
 *   - OrbitControls for drag-to-look navigation (zoom and pan disabled)
 *
 * Planet plotting is NOT included here — that is Phase E3/E4.
 *
 * Import paths assume the file lives at:
 *   frontend/js/components/sky-map-3d.js
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { altAzToCartesian } from '../astro-projection.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Radius of the celestial sphere and horizon circle. */
const SPHERE_RADIUS = 500;

/** Altitude rings drawn at these elevations (degrees). */
const ALT_RINGS = [0, 30, 60];

/** Azimuth lines drawn at these bearings (degrees, N=0, clockwise). */
const AZ_LINES = [0, 45, 90, 135, 180, 225, 270, 315];

/** Number of points used to approximate each ring as a polyline. */
const RING_SEGMENTS = 128;

/** Grid line colour — bright enough to be clearly visible against the dark sky background. */
const GRID_COLOR = 0x4488bb;

/** Grid lines are drawn at this fraction of SPHERE_RADIUS to avoid z-fighting with the sphere surface. */
const GRID_RADIUS = SPHERE_RADIUS * 0.98;

/** Cardinal label definitions: text (Swedish), azimuth, and canvas text colour. */
const CARDINALS = [
    { text: 'N', azimuth: 0   },
    { text: 'O', azimuth: 90  },
    { text: 'S', azimuth: 180 },
    { text: 'V', azimuth: 270 },
];

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

/**
 * Build a THREE.Line that traces one altitude ring at a given elevation.
 *
 * @param {number} altitudeDeg - Elevation in degrees (0 = horizon, 60 = high).
 * @param {THREE.Material} material
 * @returns {THREE.Line}
 */
function buildAltitudeRing(altitudeDeg, material) {
    const points = [];
    for (let i = 0; i <= RING_SEGMENTS; i++) {
        const az = (i / RING_SEGMENTS) * 360;
        const { x, y, z } = altAzToCartesian(altitudeDeg, az, GRID_RADIUS);
        points.push(new THREE.Vector3(x, y, z));
    }
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    return new THREE.Line(geo, material);
}

/**
 * Build a THREE.Line that traces one azimuth great-circle arc from the
 * horizon (alt=0°) up to the zenith (alt=90°).
 *
 * @param {number} azimuthDeg - Azimuth bearing in degrees.
 * @param {THREE.Material} material
 * @returns {THREE.Line}
 */
function buildAzimuthLine(azimuthDeg, material) {
    const points = [];
    for (let i = 0; i <= RING_SEGMENTS; i++) {
        const alt = (i / RING_SEGMENTS) * 90;
        const { x, y, z } = altAzToCartesian(alt, azimuthDeg, GRID_RADIUS);
        points.push(new THREE.Vector3(x, y, z));
    }
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    return new THREE.Line(geo, material);
}

/**
 * Create a canvas texture containing a single text label, then wrap it in a
 * THREE.Sprite so it always faces the camera.
 *
 * @param {string} text - Label text (e.g. 'N').
 * @returns {THREE.Sprite}
 */
function buildCardinalSprite(text) {
    // Render the label onto an off-screen canvas.
    const canvas = document.createElement('canvas');
    canvas.width  = 128;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');

    ctx.clearRect(0, 0, 128, 128);
    ctx.fillStyle = '#aabbcc';
    ctx.font = 'bold 72px sans-serif';
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 64, 64);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
    const sprite = new THREE.Sprite(material);

    // Scale the sprite to a readable size relative to the sphere radius.
    const scale = SPHERE_RADIUS * 0.07;
    sprite.scale.set(scale, scale, 1);

    return sprite;
}

/**
 * Build the complete grid group: altitude rings + azimuth lines.
 *
 * @returns {THREE.Group}
 */
function buildGrid() {
    const group = new THREE.Group();
    const mat   = new THREE.LineBasicMaterial({ color: GRID_COLOR });

    for (const alt of ALT_RINGS) {
        group.add(buildAltitudeRing(alt, mat));
    }
    for (const az of AZ_LINES) {
        group.add(buildAzimuthLine(az, mat));
    }

    return group;
}

/**
 * Build the group of cardinal direction sprites placed just above the horizon.
 *
 * @returns {THREE.Group}
 */
function buildCardinalLabels() {
    const group = new THREE.Group();
    // Altitude slightly above 0° so sprites clear the ground plane.
    const labelAlt = 4;
    const labelRadius = SPHERE_RADIUS * 0.92;

    for (const { text, azimuth } of CARDINALS) {
        const { x, y, z } = altAzToCartesian(labelAlt, azimuth, labelRadius);
        const sprite = buildCardinalSprite(text);
        sprite.position.set(x, y, z);
        group.add(sprite);
    }

    return group;
}

// ---------------------------------------------------------------------------
// SkyMap3D class
// ---------------------------------------------------------------------------

/**
 * SkyMap3D manages a WebGL Three.js scene that renders an immersive 3D sky dome.
 *
 * Lifecycle:
 *   const map3d = new SkyMap3D(containerEl);
 *   map3d.activate();     // start rendering
 *   map3d.deactivate();   // pause rendering
 *   map3d.dispose();      // full teardown
 *
 * Planet/body plotting is left for Phase E3.
 */
export default class SkyMap3D {
    /**
     * @param {HTMLElement} container - The DOM element that will contain the canvas.
     *   Does NOT modify the container until activate() is called.
     */
    constructor(container) {
        this.container = container;

        // All Three.js state is null until activate() initialises it.
        this._renderer = null;
        this._scene    = null;
        this._camera   = null;
        this._controls = null;

        // Tracks whether the render loop is currently active, used to prevent
        // double-registration of the window resize listener.
        this._active = false;

        // Bound resize handler so it can be removed cleanly.
        this._onResize = this._handleResize.bind(this);
    }

    // -----------------------------------------------------------------------
    // Public API
    // -----------------------------------------------------------------------

    /**
     * Activate the 3D view.
     *
     * On the first call: builds the full scene (renderer, camera, controls,
     * geometry). On subsequent calls: simply resizes the canvas to the current
     * container dimensions and restarts the render loop.
     *
     * @throws {Error} If WebGL is not supported by the browser.
     */
    activate() {
        if (!window.WebGLRenderingContext) {
            throw new Error('WebGL stöds inte av din webbläsare');
        }

        if (this._renderer === null) {
            this._initScene();
        }

        this._handleResize();
        this._startLoop();

        if (!this._active) {
            window.addEventListener('resize', this._onResize);
            this._active = true;
        }
    }

    /**
     * Deactivate the 3D view.
     *
     * Stops the render loop but keeps all Three.js objects alive so activate()
     * can restart quickly without rebuilding the scene.
     */
    deactivate() {
        this._stopLoop();
        window.removeEventListener('resize', this._onResize);
        this._active = false;
    }

    /**
     * Full teardown: stop the render loop, release GPU resources, and remove
     * the canvas from the DOM.
     */
    dispose() {
        this._stopLoop();
        window.removeEventListener('resize', this._onResize);

        if (this._renderer !== null) {
            this._renderer.dispose();
            if (this._renderer.domElement.parentNode) {
                this._renderer.domElement.parentNode.removeChild(this._renderer.domElement);
            }
            this._renderer = null;
        }

        this._controls = null;
        this._camera   = null;
        this._scene    = null;
    }

    // -----------------------------------------------------------------------
    // Private — scene initialisation
    // -----------------------------------------------------------------------

    /**
     * Build the renderer, scene, camera, controls, and all static geometry.
     * Called exactly once on the first activate() call.
     */
    _initScene() {
        // --- Renderer ---
        // Use a local variable so this._renderer remains null until the entire
        // initialisation succeeds. The null check in activate() thereby
        // correctly reflects whether a full init has completed.
        const renderer = new THREE.WebGLRenderer({ antialias: true });

        // Validate the WebGL context before calling any other renderer methods.
        if (renderer.getContext() === null) {
            throw new Error('WebGL-kontext kunde inte skapas');
        }

        renderer.setClearColor(0x0a0a1a, 1);

        // --- Scene ---
        const scene = new THREE.Scene();

        // --- Camera ---
        // Aspect ratio is corrected in _handleResize(); use 1 as a placeholder.
        const camera = new THREE.PerspectiveCamera(60, 1, 0.1, SPHERE_RADIUS * 2.5);
        // The +Z offset causes OrbitControls to orient the camera toward -Z,
        // which is North in this coordinate system — a correct horizon-facing
        // initial view. (Exact origin would produce a degenerate up vector.)
        camera.position.set(0, 0, 0.001);

        // --- OrbitControls ---
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableZoom = false;
        controls.enablePan  = false;
        controls.target.set(0, 0, 0);
        // Negative rotateSpeed gives the sky-dome feel: dragging right rotates
        // the camera left, as if the observer is turning their head.
        // Negative rotateSpeed inverts drag direction for the sky-dome feel:
        // dragging UP increases phi internally → phi=π means camera looks toward zenith.
        controls.rotateSpeed = -0.5;
        // With inverted controls phi increases upward, so:
        //   maxPolarAngle near π  → allows full zenith viewing
        //   minPolarAngle ~81°    → prevents looking more than ~9° below the horizon
        controls.maxPolarAngle = Math.PI * 0.99;
        controls.minPolarAngle = Math.PI * 0.45;
        controls.update();

        // --- Celestial sphere (inside-out, camera inside) ---
        const sphereGeo = new THREE.SphereGeometry(SPHERE_RADIUS, 32, 32);
        const sphereMat = new THREE.MeshBasicMaterial({
            color: 0x0a0a1a,
            side: THREE.BackSide,
        });
        scene.add(new THREE.Mesh(sphereGeo, sphereMat));

        // --- Horizon ground plane ---
        // A flat disc at y=0 that visually separates sky from "ground".
        const groundGeo = new THREE.CircleGeometry(SPHERE_RADIUS, 64);
        const groundMat = new THREE.MeshBasicMaterial({
            color: 0x111122,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.8,
        });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        // CircleGeometry lies in the XY plane; rotate so it lies in the XZ plane (y=0).
        ground.rotation.x = -Math.PI / 2;
        scene.add(ground);

        // --- Alt-azimuth grid ---
        scene.add(buildGrid());

        // --- Cardinal direction labels ---
        scene.add(buildCardinalLabels());

        // Commit scene/camera/controls to the instance before touching the DOM.
        // If any of these assignments were to throw, no canvas will have been
        // orphaned in the DOM and this._renderer remains null (the sentinel).
        this._scene    = scene;
        this._camera   = camera;
        this._controls = controls;

        // Attach the canvas to the DOM only after all instance fields above are
        // set, so a teardown racing a failed init can still clean up safely.
        renderer.domElement.setAttribute('aria-hidden', 'true');
        this.container.appendChild(renderer.domElement);

        // this._renderer is assigned last so that the null check in activate()
        // is a reliable sentinel for complete initialisation — any earlier throw
        // leaves it null.
        this._setPixelRatio(renderer);
        this._renderer = renderer;
    }

    // -----------------------------------------------------------------------
    // Private — render loop
    // -----------------------------------------------------------------------

    /** Start (or restart) the WebGL animation loop. */
    _startLoop() {
        if (this._renderer === null) return;
        this._renderer.setAnimationLoop(() => {
            if (this._controls !== null) {
                this._controls.update();
            }
            this._renderer.render(this._scene, this._camera);
        });
    }

    /** Stop the WebGL animation loop without disposing resources. */
    _stopLoop() {
        if (this._renderer !== null) {
            this._renderer.setAnimationLoop(null);
        }
    }

    // -----------------------------------------------------------------------
    // Private — resize handling
    // -----------------------------------------------------------------------

    /**
     * Recalculate the renderer size and camera aspect ratio to match the
     * current container dimensions.
     */
    _handleResize() {
        if (this._renderer === null) return;

        const width  = this.container.clientWidth;
        const height = this.container.clientHeight;

        if (width === 0 || height === 0) return;

        this._camera.aspect = width / height;
        this._camera.updateProjectionMatrix();
        this._renderer.setSize(width, height);
    }

    // -----------------------------------------------------------------------
    // Private — pixel ratio
    // -----------------------------------------------------------------------

    /**
     * Apply the device pixel ratio (capped at 2 to avoid excessive GPU load
     * on very high-DPI displays).
     *
     * @param {THREE.WebGLRenderer} [renderer] - Renderer to configure.
     *   Defaults to this._renderer. Pass the local renderer instance when
     *   calling from _initScene() before this._renderer has been assigned.
     */
    _setPixelRatio(renderer = this._renderer) {
        if (renderer === null) return;
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    }
}
