"use client";

import { useMemo, useRef, type MutableRefObject } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import * as THREE from "three";
import type { MousePosition } from "@/hooks/useMousePosition";

/* ─── Shaders ─────────────────────────────────────────────── */

const BASE_VERT = /* glsl */ `
  uniform float uTime;
  uniform vec2  uMouse;

  varying vec3  vNormal;
  varying vec3  vWorldPos;

  void main() {
    vNormal = normalize(normalMatrix * normal);

    /* Slow breath — three overlapping sine waves on each axis */
    float d = sin(position.x * 2.1 + uTime * 0.90) * 0.055
            + sin(position.y * 2.6 + uTime * 0.72) * 0.055
            + sin(position.z * 3.0 + uTime * 0.83) * 0.055;

    vec3 displaced  = position + normal * d;
    vec4 worldPos   = modelMatrix * vec4(displaced, 1.0);
    vWorldPos       = worldPos.xyz;

    gl_Position = projectionMatrix * viewMatrix * worldPos;
  }
`;

const BASE_FRAG = /* glsl */ `
  uniform vec2  uMouse;
  uniform float uTime;

  varying vec3  vNormal;
  varying vec3  vWorldPos;

  void main() {
    vec3 normal   = normalize(vNormal);
    vec3 viewDir  = normalize(cameraPosition - vWorldPos);

    /* Fresnel rim — drives plasma glow on silhouette */
    float fresnel = pow(1.0 - abs(dot(normal, viewDir)), 3.2);

    /* Mouse directional light in world space */
    vec3 mouseDir = normalize(vec3(uMouse.x * 3.5, uMouse.y * 3.5, 2.5));
    float diffuse = max(dot(normal, mouseDir), 0.0);

    vec3 plasma = vec3(0.0,  0.824, 1.0);   /* #00D2FF */
    vec3 ember  = vec3(1.0,  0.271, 0.0);   /* #FF4500 */

    vec3 color = mix(plasma, ember, diffuse * 0.85);
    float alpha = fresnel * 0.55 + diffuse * 0.12 + 0.018;

    gl_FragColor = vec4(color, alpha);
  }
`;

const EDGE_VERT = /* glsl */ `
  varying vec3 vWorldPos;

  void main() {
    vec4 wp   = modelMatrix * vec4(position, 1.0);
    vWorldPos = wp.xyz;
    gl_Position = projectionMatrix * viewMatrix * wp;
  }
`;

const EDGE_FRAG = /* glsl */ `
  uniform vec3  uMouseWorld;
  uniform float uTime;

  varying vec3 vWorldPos;

  void main() {
    float dist = distance(vWorldPos, uMouseWorld);
    float heat = 1.0 - smoothstep(0.0, 2.8, dist);

    vec3 plasma = vec3(0.0, 0.824, 1.0);
    vec3 ember  = vec3(1.0, 0.271, 0.0);
    vec3 color  = mix(plasma, ember, heat * heat);

    /* Subtle per-vertex flicker */
    float pulse = 0.78 + 0.22 * sin(uTime * 2.1 + vWorldPos.x * 2.8 + vWorldPos.z * 1.7);

    gl_FragColor = vec4(color * pulse, 1.0);
  }
`;

/* ─── Particle field shaders ──────────────────────────────── */

const PART_VERT = /* glsl */ `
  attribute float aSize;
  uniform   float uTime;
  varying   float vAlpha;

  void main() {
    vAlpha = 0.3 + 0.7 * fract(sin(dot(position.xy, vec2(12.9898, 78.233))) * 43758.5);
    float flicker = sin(uTime * 1.5 + position.z * 3.14) * 0.4 + 0.6;
    vAlpha *= flicker;

    vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = aSize * (260.0 / -mvPos.z);
    gl_Position  = projectionMatrix * mvPos;
  }
`;

const PART_FRAG = /* glsl */ `
  varying float vAlpha;

  void main() {
    float d = length(gl_PointCoord - 0.5) * 2.0;
    float circle = 1.0 - smoothstep(0.6, 1.0, d);
    gl_FragColor = vec4(0.0, 0.824, 1.0, circle * vAlpha * 0.55);
  }
`;

/* ─── Component ───────────────────────────────────────────── */

interface SteelSceneProps {
  mousePosition: MutableRefObject<MousePosition>;
}

export default function SteelScene({ mousePosition }: SteelSceneProps) {
  const groupRef  = useRef<THREE.Group>(null);
  const { camera } = useThree();

  const mouseWorld       = useRef(new THREE.Vector3(0, 0, 2));
  const targetMouseWorld = useRef(new THREE.Vector3(0, 0, 2));
  const _dir             = useRef(new THREE.Vector3());
  const _ndc             = useRef(new THREE.Vector3());

  /* ── Geometry ── */
  const geo   = useMemo(() => new THREE.IcosahedronGeometry(2.2, 2), []);
  const edges = useMemo(() => new THREE.EdgesGeometry(geo, 12), [geo]);

  /* ── Materials ── */
  const baseMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader:   BASE_VERT,
        fragmentShader: BASE_FRAG,
        uniforms: {
          uTime:  { value: 0 },
          uMouse: { value: new THREE.Vector2(0, 0) },
        },
        transparent: true,
        side:        THREE.DoubleSide,
        depthWrite:  false,
        blending:    THREE.AdditiveBlending,
      }),
    []
  );

  const edgeMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader:   EDGE_VERT,
        fragmentShader: EDGE_FRAG,
        uniforms: {
          uMouseWorld: { value: new THREE.Vector3(0, 0, 2) },
          uTime:       { value: 0 },
        },
        blending:   THREE.AdditiveBlending,
        depthWrite: false,
      }),
    []
  );

  /* ── Particles ── */
  const { partGeo, partMat } = useMemo(() => {
    const COUNT = 320;
    const positions = new Float32Array(COUNT * 3);
    const sizes     = new Float32Array(COUNT);

    for (let i = 0; i < COUNT; i++) {
      const r     = 3.5 + Math.random() * 5;
      const theta = Math.random() * Math.PI * 2;
      const phi   = Math.acos(2 * Math.random() - 1);
      positions[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);
      sizes[i] = 0.8 + Math.random() * 2.2;
    }

    const pg = new THREE.BufferGeometry();
    pg.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    pg.setAttribute("aSize",    new THREE.BufferAttribute(sizes, 1));

    const pm = new THREE.ShaderMaterial({
      vertexShader:   PART_VERT,
      fragmentShader: PART_FRAG,
      uniforms: { uTime: { value: 0 } },
      transparent: true,
      depthWrite:  false,
      blending:    THREE.AdditiveBlending,
    });

    return { partGeo: pg, partMat: pm };
  }, []);

  /* ── Frame loop — zero re-renders, only ref mutations ── */
  useFrame(({ clock }) => {
    const t     = clock.getElapsedTime();
    const mouse = mousePosition.current;

    baseMat.uniforms.uTime.value      = t;
    baseMat.uniforms.uMouse.value.set(mouse.x, mouse.y);
    edgeMat.uniforms.uTime.value      = t;
    partMat.uniforms.uTime.value      = t;

    /* Unproject 2-D mouse to the plane z = 2 in world space */
    _ndc.current.set(mouse.x, mouse.y, 0.5).unproject(camera);
    _dir.current.copy(_ndc.current).sub(camera.position).normalize();
    const tParam = (2 - camera.position.z) / _dir.current.z;
    targetMouseWorld.current
      .copy(camera.position)
      .addScaledVector(_dir.current, tParam);

    mouseWorld.current.lerp(targetMouseWorld.current, 0.06);
    edgeMat.uniforms.uMouseWorld.value.copy(mouseWorld.current);

    /* Slow auto-rotation + tilt following mouse */
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.004;
      groupRef.current.rotation.x =
        THREE.MathUtils.lerp(groupRef.current.rotation.x, mouse.y * 0.15, 0.03);
    }
  });

  return (
    <>
      <group ref={groupRef}>
        {/* Translucent shaded body */}
        <mesh geometry={geo} material={baseMat} />

        {/* Wireframe edges with heat gradient */}
        <lineSegments geometry={edges} material={edgeMat} />
      </group>

      {/* Atmospheric particle field */}
      <points geometry={partGeo} material={partMat} />

      {/* Bloom post-process — picks up all additive-blended bright geometry */}
      <EffectComposer>
        <Bloom
          mipmapBlur
          luminanceThreshold={0.0}
          luminanceSmoothing={0.6}
          intensity={2.2}
        />
      </EffectComposer>
    </>
  );
}
