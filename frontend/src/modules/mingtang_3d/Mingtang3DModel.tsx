import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Environment, Grid, Html } from '@react-three/drei';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
import * as THREE from 'three';
import { useAppStore } from '@/store';
import { MINGTANG_DIMENSIONS, DEFAULT_WINDOWS, SENSOR_LOCATIONS, WOOD_MATERIAL, WALL_MATERIAL, ROOF_MATERIAL, WINDOW_MATERIAL, GOLD_DECORATION } from './buildingData';
import type { WindowSolution } from '@/types';

interface MingtangStructureProps {
  windows: WindowSolution[] | null;
  wireframe: boolean;
  showSensors: boolean;
}

const MingtangStructure: React.FC<MingtangStructureProps> = ({ windows, wireframe, showSensors }) => {
  const groupRef = useRef<THREE.Group>(null);
  const { autoRotate } = useAppStore();

  const { length, width, height, wallThickness } = MINGTANG_DIMENSIONS;
  const halfLen = length / 2;
  const halfWid = width / 2;
  const halfHgt = height / 2;

  const displayWindows = windows ? windows.map(w => ({
    position: w.position as [number, number, number],
    size: [w.size[0], w.size[1]] as [number, number],
    normal: [1, 0, 0] as [number, number, number],
    up: [0, 1, 0] as [number, number, number],
    transmittance: w.transmittance
  })) : DEFAULT_WINDOWS;

  useFrame((_, delta) => {
    if (groupRef.current && autoRotate) {
      groupRef.current.rotation.y += delta * 0.1;
    }
  });

  const roofPoints = useMemo(() => [
    new THREE.Vector3(-halfLen - 1, height, -halfWid - 1),
    new THREE.Vector3(halfLen + 1, height, -halfWid - 1),
    new THREE.Vector3(halfLen + 1, height, halfWid + 1),
    new THREE.Vector3(-halfLen - 1, height, halfWid + 1),
    new THREE.Vector3(0, height + 4, 0),
  ], [halfLen, halfWid, height]);

  return (
    <group ref={groupRef}>
      <mesh position={[0, -wallThickness / 2, 0]} receiveShadow>
        <boxGeometry args={[length + 4, wallThickness, width + 4]} />
        <meshStandardMaterial {...WALL_MATERIAL} color="#C4A484" wireframe={wireframe} />
      </mesh>

      <mesh position={[0, halfHgt, halfWid]} castShadow receiveShadow>
        <boxGeometry args={[length, height, wallThickness]} />
        <meshStandardMaterial {...WALL_MATERIAL} wireframe={wireframe} />
      </mesh>

      <mesh position={[0, halfHgt, -halfWid]} castShadow receiveShadow>
        <boxGeometry args={[length, height, wallThickness]} />
        <meshStandardMaterial {...WALL_MATERIAL} wireframe={wireframe} />
      </mesh>

      <mesh position={[halfLen, halfHgt, 0]} castShadow receiveShadow>
        <boxGeometry args={[wallThickness, height, width]} />
        <meshStandardMaterial {...WALL_MATERIAL} wireframe={wireframe} />
      </mesh>

      <mesh position={[-halfLen, halfHgt, 0]} castShadow receiveShadow>
        <boxGeometry args={[wallThickness, height, width]} />
        <meshStandardMaterial {...WALL_MATERIAL} wireframe={wireframe} />
      </mesh>

      {displayWindows.map((win, idx) => (
        <mesh key={idx} position={win.position} castShadow>
          <boxGeometry args={[win.size[0], win.size[1], wallThickness * 0.8]} />
          <meshStandardMaterial
            {...WINDOW_MATERIAL}
            opacity={0.3 + win.transmittance * 0.6}
            wireframe={wireframe}
          />
        </mesh>
      ))}

      <mesh position={[0, height + 0.5, 0]} castShadow receiveShadow>
        <boxGeometry args={[length + 2, wallThickness, width + 2]} />
        <meshStandardMaterial {...ROOF_MATERIAL} wireframe={wireframe} />
      </mesh>

      <mesh position={[0, height + 0.5, 0]} rotation={[Math.PI, 0, 0]}>
        <coneGeometry args={[halfLen + 2, 5, 4]} />
        <meshStandardMaterial {...ROOF_MATERIAL} wireframe={wireframe} />
      </mesh>

      <mesh position={[0, height + 5, 0]} castShadow>
        <sphereGeometry args={[0.5, 16, 16]} />
        <meshStandardMaterial {...GOLD_DECORATION} emissive="#FFD700" emissiveIntensity={0.5} wireframe={wireframe} />
      </mesh>

      {[[-halfLen + 3, 0, halfWid], [halfLen - 3, 0, halfWid],
        [-halfLen + 3, 0, -halfWid], [halfLen - 3, 0, -halfWid]].map((pos, idx) => (
        <group key={`pillar-${idx}`} position={pos as [number, number, number]}>
          <mesh position={[0, halfHgt, 0]} castShadow>
            <cylinderGeometry args={[0.3, 0.35, height, 8]} />
            <meshStandardMaterial {...WOOD_MATERIAL} wireframe={wireframe} />
          </mesh>
          <mesh position={[0, height + 0.1, 0]} castShadow>
            <cylinderGeometry args={[0.4, 0.3, 0.3, 8]} />
            <meshStandardMaterial {...GOLD_DECORATION} wireframe={wireframe} />
          </mesh>
        </group>
      ))}

      {showSensors && SENSOR_LOCATIONS.map((sensor, idx) => (
        <group key={`sensor-${idx}`} position={sensor.position as [number, number, number]}>
          <mesh castShadow>
            <sphereGeometry args={[0.15, 8, 8]} />
            <meshStandardMaterial
              color="#22C55E"
              emissive="#22C55E"
              emissiveIntensity={0.5}
            />
          </mesh>
          <Html position={[0, 0.5, 0]} center distanceFactor={15}>
            <div className="bg-black/80 px-2 py-1 rounded text-xs text-white whitespace-nowrap">
              {sensor.label}
            </div>
          </Html>
        </group>
      ))}

      <mesh position={[0, 0.6, 0]} castShadow>
        <cylinderGeometry args={[1.5, 2, 1.2, 8]} />
        <meshStandardMaterial {...GOLD_DECORATION} wireframe={wireframe} />
      </mesh>

      <mesh position={[0, 1.5, 0]} castShadow>
        <boxGeometry args={[1, 1.2, 1]} />
        <meshStandardMaterial {...WOOD_MATERIAL} wireframe={wireframe} />
      </mesh>

      {[[0, 0], [Math.PI / 2, 0], [Math.PI, 0], [-Math.PI / 2, 0]].map((rot, idx) => (
        <group key={`door-${idx}`} rotation={[0, rot[0], 0]} position={[0, 0, halfWid - wallThickness]}>
          <mesh position={[0, 1.8, 0]} castShadow>
            <boxGeometry args={[2, 3.6, wallThickness * 0.5]} />
            <meshStandardMaterial {...WOOD_MATERIAL} wireframe={wireframe} />
          </mesh>
          <mesh position={[0, 3.6, 0]} castShadow>
            <boxGeometry args={[2.4, 0.2, wallThickness * 0.6]} />
            <meshStandardMaterial {...GOLD_DECORATION} wireframe={wireframe} />
          </mesh>
        </group>
      ))}
    </group>
  );
};

interface SunLightProps {
  altitude: number;
  azimuth: number;
}

const SunLight: React.FC<SunLightProps> = ({ altitude, azimuth }) => {
  const lightRef = useRef<THREE.DirectionalLight>(null);
  const sunPos = useMemo(() => {
    const r = 50;
    const altRad = (altitude * Math.PI) / 180;
    const azRad = (azimuth * Math.PI) / 180;
    return new THREE.Vector3(
      r * Math.cos(altRad) * Math.sin(azRad),
      r * Math.sin(altRad),
      r * Math.cos(altRad) * Math.cos(azRad)
    );
  }, [altitude, azimuth]);

  useFrame(() => {
    if (lightRef.current) {
      lightRef.current.position.copy(sunPos);
      lightRef.current.target.position.set(0, 0, 0);
      lightRef.current.target.updateMatrixWorld();
    }
  });

  return (
    <>
      <directionalLight
        ref={lightRef}
        position={sunPos}
        intensity={Math.max(0, Math.sin((altitude * Math.PI) / 180)) * 2}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-far={100}
        shadow-camera-left={-30}
        shadow-camera-right={30}
        shadow-camera-top={30}
        shadow-camera-bottom={-30}
      />
      <mesh position={sunPos}>
        <sphereGeometry args={[2, 32, 32]} />
        <meshBasicMaterial color="#FFD700" transparent opacity={0.8} />
      </mesh>
    </>
  );
};

interface Mingtang3DModelProps {
  solarAltitude?: number;
  solarAzimuth?: number;
  windows?: WindowSolution[] | null;
}

const Mingtang3DModel: React.FC<Mingtang3DModelProps> = ({
  solarAltitude = 45,
  solarAzimuth = 180,
  windows = null
}) => {
  const { wireframeMode } = useAppStore();

  return (
    <Canvas
      shadows
      camera={{ position: [30, 25, 30], fov: 50 }}
      gl={{ antialias: true, alpha: true }}
    >
      <color attach="background" args={['#0a0a1a']} />
      <fog attach="fog" args={['#0a0a1a', 50, 150]} />

      <ambientLight intensity={0.3} />
      <hemisphereLight args={['#87CEEB', '#4a3728', 0.4]} />

      <SunLight altitude={solarAltitude} azimuth={solarAzimuth} />

      <MingtangStructure
        windows={windows}
        wireframe={wireframeMode}
        showSensors={true}
      />

      <Grid
        args={[60, 60]}
        cellSize={1}
        cellThickness={0.5}
        cellColor="#2a2a4a"
        sectionSize={5}
        sectionThickness={1}
        sectionColor="#4a4a7a"
        fadeDistance={80}
        fadeStrength={1}
        followCamera={false}
        position={[0, -0.26, 0]}
      />

      <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />

      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        minDistance={10}
        maxDistance={80}
        maxPolarAngle={Math.PI / 2 - 0.1}
      />

      <EffectComposer>
        <Bloom luminanceThreshold={0.2} luminanceSmoothing={0.9} height={300} />
        <Vignette eskil={false} offset={0.1} darkness={0.5} />
      </EffectComposer>
    </Canvas>
  );
};

export default Mingtang3DModel;
