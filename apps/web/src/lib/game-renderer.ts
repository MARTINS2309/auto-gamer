import {
  WebGLRenderer,
  Scene,
  OrthographicCamera,
  DataTexture,
  PlaneGeometry,
  MeshBasicMaterial,
  Mesh,
  NearestFilter,
  RGBAFormat,
} from "three"

const MAX_VISIBLE_ENVS = 16

// ── DVR Controller ──────────────────────────────────────────────────────
// Plain JS class — no React, no state. Mutate fields directly from event
// handlers and read them inside rAF loops.

export class DVRController {
  cursor = 0
  speed = 1
  playing = true
  /** Entries consumed per second at 1x speed — set to captureFps. */
  baseFps = 15
  private initialized = false

  /** Advance cursor by dt seconds. Call every rAF tick. */
  advance(dt: number, ringGeneration: number, ringSize: number): void {
    if (ringSize === 0) return
    // Auto-snap to live on first use (handles late-mount into running run)
    if (!this.initialized) {
      this.cursor = ringGeneration - 1
      this.initialized = true
    }
    if (!this.playing || dt <= 0) return
    this.cursor += this.speed * this.baseFps * dt
    this.clamp(ringGeneration, ringSize)
  }

  /** Clamp cursor to valid buffer range, snap to live at ≥1x. */
  clamp(ringGeneration: number, ringSize: number): void {
    const oldest = ringGeneration - ringSize
    const newest = ringGeneration - 1
    if (this.cursor < oldest) this.cursor = oldest
    if (this.cursor > newest) this.cursor = newest
    if (newest - this.cursor < 2 && this.speed >= 1) this.cursor = newest
  }

  /** Get ring buffer array index for current cursor position. */
  ringIndex(capacity: number): number {
    const gen = Math.floor(this.cursor)
    return ((gen % capacity) + capacity) % capacity
  }

  /** Is the cursor at the live edge of the ring buffer? */
  isLive(ringGeneration: number, ringSize: number): boolean {
    if (ringSize === 0) return true
    return ringGeneration - 1 - this.cursor < 2
  }

  /** Seek to a specific generation. Pauses playback. */
  seekTo(generation: number): void {
    this.cursor = generation
    this.playing = false
  }

  /** Jump cursor to live, reset speed to 1x, resume playback. */
  goLive(ringGeneration: number): void {
    this.cursor = ringGeneration - 1
    this.speed = 1
    this.playing = true
  }

  /** Normalized position [0, 1] within the ring buffer. */
  normalizedPosition(ringGeneration: number, ringSize: number): number {
    if (ringSize <= 1) return 1
    const oldest = ringGeneration - ringSize
    const newest = ringGeneration - 1
    return (this.cursor - oldest) / (newest - oldest)
  }

  /** Seconds behind live edge. */
  lagSeconds(ringGeneration: number): number {
    return Math.max(0, (ringGeneration - 1 - this.cursor) / this.baseFps)
  }
}

// ── Game Renderer ───────────────────────────────────────────────────────
// Three.js-based tiled renderer. Generic frame feed — works for training
// (multi-env tiled) and play mode (single env).

interface TileData {
  mesh: Mesh<PlaneGeometry, MeshBasicMaterial>
  texture: DataTexture
  rgbaData: Uint8Array
  rgba32: Uint32Array
}

export class GameRenderer {
  private renderer: WebGLRenderer
  private scene: Scene
  private camera: OrthographicCamera
  private tiles: TileData[] = []
  private cols = 0
  private rows = 0
  private frameWidth = 0
  private frameHeight = 0

  constructor(container: HTMLElement) {
    this.renderer = new WebGLRenderer({ antialias: false, alpha: false })
    this.renderer.setPixelRatio(1)
    this.renderer.setClearColor(0x000000)

    const canvas = this.renderer.domElement
    canvas.style.width = "100%"
    canvas.style.height = "100%"
    canvas.style.imageRendering = "pixelated"
    canvas.style.display = "block"
    container.appendChild(canvas)

    this.scene = new Scene()
    this.camera = new OrthographicCamera(0, 1, 1, 0, -1, 1)
  }

  /**
   * Set grid layout. Call when envCount or frame dimensions change.
   * Tiles are created/recreated only when the layout actually differs.
   */
  setLayout(envCount: number, frameWidth: number, frameHeight: number): void {
    const count = Math.min(Math.max(envCount, 1), MAX_VISIBLE_ENVS)
    const cols =
      count <= 1 ? 1 : count <= 2 ? 2 : count <= 4 ? 2 : count <= 6 ? 3 : 4
    const rows = Math.ceil(count / cols)

    if (
      cols === this.cols &&
      rows === this.rows &&
      count === this.tiles.length &&
      frameWidth === this.frameWidth &&
      frameHeight === this.frameHeight
    )
      return

    this.cols = cols
    this.rows = rows
    this.frameWidth = frameWidth
    this.frameHeight = frameHeight

    // Tear down old tiles
    for (const t of this.tiles) {
      this.scene.remove(t.mesh)
      t.texture.dispose()
      t.mesh.material.dispose()
      t.mesh.geometry.dispose()
    }
    this.tiles = []

    // Create tiles
    const pixelCount = frameWidth * frameHeight
    for (let i = 0; i < count; i++) {
      const col = i % cols
      const row = Math.floor(i / cols)

      // Persistent RGBA buffer + Uint32 view for fast RGB→RGBA conversion
      const rgbaData = new Uint8Array(pixelCount * 4)
      const rgba32 = new Uint32Array(rgbaData.buffer)

      const texture = new DataTexture(
        rgbaData,
        frameWidth,
        frameHeight,
        RGBAFormat
      )
      texture.minFilter = NearestFilter
      texture.magFilter = NearestFilter
      texture.generateMipmaps = false
      texture.needsUpdate = true

      const geometry = new PlaneGeometry(1, 1)
      // Flip UVs vertically — our pixel data is top-to-bottom but
      // PlaneGeometry maps v=0 to the bottom edge of the quad.
      const uv = geometry.attributes.uv
      for (let j = 0; j < uv.count; j++) {
        uv.setY(j, 1 - uv.getY(j))
      }

      const material = new MeshBasicMaterial({ map: texture })
      const mesh = new Mesh(geometry, material)
      // Position tile center in the grid (camera Y axis is bottom-up)
      mesh.position.set(col + 0.5, rows - 1 - row + 0.5, 0)
      this.scene.add(mesh)

      this.tiles.push({ mesh, texture, rgbaData, rgba32 })
    }

    // Camera frustum matches grid
    this.camera.left = 0
    this.camera.right = cols
    this.camera.top = rows
    this.camera.bottom = 0
    this.camera.updateProjectionMatrix()

    // Drawing buffer = native pixel resolution (CSS stretches with pixelated)
    this.renderer.setSize(cols * frameWidth, rows * frameHeight, false)
  }

  /** Upload RGB pixel data for a specific env tile. */
  updateTile(
    envIndex: number,
    rgbData: Uint8Array,
    width: number,
    height: number
  ): void {
    const tile = this.tiles[envIndex]
    if (!tile) return

    const pixelCount = width * height
    const { rgba32 } = tile
    // Fast RGB→RGBA via Uint32Array (little-endian: 0xAABBGGRR)
    for (let p = 0; p < pixelCount; p++) {
      const ri = p * 3
      rgba32[p] =
        0xff000000 |
        (rgbData[ri + 2] << 16) |
        (rgbData[ri + 1] << 8) |
        rgbData[ri]
    }
    tile.texture.needsUpdate = true
  }

  /** Render the scene. */
  render(): void {
    this.renderer.render(this.scene, this.camera)
  }

  /** Tear down WebGL resources and remove canvas from DOM. */
  dispose(): void {
    for (const t of this.tiles) {
      this.scene.remove(t.mesh)
      t.texture.dispose()
      t.mesh.material.dispose()
      t.mesh.geometry.dispose()
    }
    this.tiles = []
    const canvas = this.renderer.domElement
    this.renderer.dispose()
    canvas.parentElement?.removeChild(canvas)
  }

  get domElement(): HTMLCanvasElement {
    return this.renderer.domElement
  }

  get tileCount(): number {
    return this.tiles.length
  }
}
