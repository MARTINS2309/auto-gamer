const VS = `
  attribute vec2 a_pos;
  varying vec2 v_uv;
  void main() {
    gl_Position = vec4(a_pos, 0.0, 1.0);
    v_uv = a_pos * 0.5 + 0.5;
    v_uv.y = 1.0 - v_uv.y;
  }
`

const FS = `
  precision mediump float;
  varying vec2 v_uv;
  uniform sampler2D u_tex;
  void main() { gl_FragColor = texture2D(u_tex, v_uv); }
`

export interface WebGLContext {
  gl: WebGLRenderingContext
  tex: WebGLTexture
  prog: WebGLProgram
  vs: WebGLShader
  fs: WebGLShader
  buf: WebGLBuffer
}

export function initWebGL(canvas: HTMLCanvasElement): WebGLContext | null {
  const gl = canvas.getContext("webgl2", { antialias: false })
    ?? canvas.getContext("webgl", { antialias: false })
  if (!gl) return null

  const vs = gl.createShader(gl.VERTEX_SHADER)!
  gl.shaderSource(vs, VS)
  gl.compileShader(vs)

  const fs = gl.createShader(gl.FRAGMENT_SHADER)!
  gl.shaderSource(fs, FS)
  gl.compileShader(fs)

  const prog = gl.createProgram()!
  gl.attachShader(prog, vs)
  gl.attachShader(prog, fs)
  gl.linkProgram(prog)
  gl.useProgram(prog)

  // Fullscreen quad
  const buf = gl.createBuffer()!
  gl.bindBuffer(gl.ARRAY_BUFFER, buf)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)
  const loc = gl.getAttribLocation(prog, "a_pos")
  gl.enableVertexAttribArray(loc)
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0)

  // Texture — NEAREST for crisp pixel art
  const tex = gl.createTexture()!
  gl.bindTexture(gl.TEXTURE_2D, tex)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)

  return { gl, tex, prog, vs, fs, buf }
}

export function destroyWebGL(ctx: WebGLContext): void {
  const { gl, tex, buf, prog, vs, fs } = ctx
  gl.deleteTexture(tex)
  gl.deleteBuffer(buf)
  gl.deleteProgram(prog)
  gl.deleteShader(vs)
  gl.deleteShader(fs)
}
