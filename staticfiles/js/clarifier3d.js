/* ============================================================
   حوض ترسيب ثلاثي الأبعاد تفاعلي — Three.js
   يُستدعى: Clarifier3D.init(containerId, initialData)
   ويُحدّث: Clarifier3D.update({flow, blanket, ras, was, state})
   ============================================================ */
(function (global) {
  let scene, camera, renderer, bridge, sludge, waterMat, controls;
  let raf, container, W, H;
  let autoRotate = true, targetSpin = 0.006, blanketTargetY = -1.6;
  const THREE = global.THREE;

  function init(containerId, data) {
    container = document.getElementById(containerId);
    if (!container || !THREE) return;
    W = container.clientWidth; H = container.clientHeight || 420;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(42, W / H, 0.1, 100);
    camera.position.set(0, 9.5, 12);
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(global.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // إضاءة ناعمة (نهار)
    scene.add(new THREE.HemisphereLight(0xffffff, 0xcfe0f0, 0.95));
    const sun = new THREE.DirectionalLight(0xffffff, 0.9);
    sun.position.set(6, 12, 6); sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    scene.add(sun);
    const fill = new THREE.DirectionalLight(0x9fd8e6, 0.4);
    fill.position.set(-8, 5, -6); scene.add(fill);

    const R = 5;              // نصف قطر الحوض
    const wallH = 2.2;        // ارتفاع الجدار
    const depth = 3.4;        // عمق الحوض

    // ---- الأرضية المحيطة (منصّة خرسانية فاتحة) ----
    const ground = new THREE.Mesh(
      new THREE.CircleGeometry(R + 2.4, 64),
      new THREE.MeshStandardMaterial({ color: 0xdfe8f2, roughness: 0.95 })
    );
    ground.rotation.x = -Math.PI / 2; ground.position.y = -0.02;
    ground.receiveShadow = true; scene.add(ground);

    // ---- جدار الحوض (أسطوانة خرسانية) ----
    const wallMat = new THREE.MeshStandardMaterial({ color: 0xaebfd2, roughness: 0.85, metalness: 0.08 });
    const wall = new THREE.Mesh(new THREE.CylinderGeometry(R, R, wallH, 64, 1, true), wallMat);
    wall.position.y = wallH / 2 - 0.2; wall.castShadow = true; wall.receiveShadow = true; scene.add(wall);
    // حافة علوية
    const rimMat = new THREE.MeshStandardMaterial({ color: 0xe8eef6, roughness: 0.8 });
    const rim = new THREE.Mesh(new THREE.TorusGeometry(R, 0.12, 12, 64), rimMat);
    rim.rotation.x = Math.PI / 2; rim.position.y = wallH - 0.2; scene.add(rim);

    // ---- القاع المخروطي ----
    const floor = new THREE.Mesh(
      new THREE.ConeGeometry(R, depth * 0.5, 64, 1, true),
      new THREE.MeshStandardMaterial({ color: 0x9fb1c6, roughness: 0.95, side: THREE.DoubleSide })
    );
    floor.position.y = -depth * 0.5; floor.rotation.x = Math.PI; scene.add(floor);

    // ---- طبقة الحمأة (مخروط بنّي متغيّر الارتفاع) ----
    const sludgeMat = new THREE.MeshStandardMaterial({ color: 0x7a5230, roughness: 1, transparent: true, opacity: 0.95 });
    sludge = new THREE.Mesh(new THREE.ConeGeometry(R - 0.15, depth * 0.5, 64, 1, true), sludgeMat);
    sludge.position.y = -depth * 0.5 + 0.02; sludge.rotation.x = Math.PI;
    sludge.scale.y = 0.35; scene.add(sludge);

    // ---- سطح الماء (قرص شفّاف لامع) ----
    waterMat = new THREE.MeshPhysicalMaterial({
      color: 0x1f9ec4, roughness: 0.12, metalness: 0.0,
      transmission: 0.25, transparent: true, opacity: 0.92,
      clearcoat: 1, clearcoatRoughness: 0.15, reflectivity: 0.6,
    });
    const water = new THREE.Mesh(new THREE.CircleGeometry(R - 0.15, 64), waterMat);
    water.rotation.x = -Math.PI / 2; water.position.y = wallH - 0.55; scene.add(water);
    // طبقة عمق زرقاء داكنة تحت السطح لإيهام العمق
    const deep = new THREE.Mesh(new THREE.CircleGeometry(R - 0.15, 64),
      new THREE.MeshBasicMaterial({ color: 0x0d5f78 }));
    deep.rotation.x = -Math.PI / 2; deep.position.y = wallH - 0.75; scene.add(deep);
    // حلقات تموّج على السطح
    for (let i = 1; i <= 3; i++) {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(i * 1.1, i * 1.1 + 0.04, 64),
        new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.25 })
      );
      ring.rotation.x = -Math.PI / 2; ring.position.y = wallH - 0.54; scene.add(ring);
    }

    // ---- بئر التغذية المركزي ----
    const wellMat = new THREE.MeshStandardMaterial({ color: 0xbfe6ee, roughness: 0.5, emissive: 0x2a8fa5, emissiveIntensity: 0.25 });
    const well = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, 1.4, 32, 1, true), wellMat);
    well.position.y = wallH - 0.4; scene.add(well);

    // ---- الجسر الدوّار (معدني عبر القطر) ----
    bridge = new THREE.Group();
    const beamMat = new THREE.MeshStandardMaterial({ color: 0xd4dde8, roughness: 0.5, metalness: 0.6 });
    const beam = new THREE.Mesh(new THREE.BoxGeometry(R * 2, 0.16, 0.4), beamMat);
    beam.position.y = wallH - 0.1; beam.castShadow = true; bridge.add(beam);
    // هيكل شبكي (قضبان قطرية)
    for (let x = -R + 0.6; x < R; x += 0.7) {
      const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.5, 6), beamMat);
      bar.position.set(x, wallH - 0.28, 0); bar.rotation.z = 0.5; bridge.add(bar);
    }
    // كابينة المحرّك في المركز
    const cab = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.5, 0.7),
      new THREE.MeshStandardMaterial({ color: 0xeef4fa, roughness: 0.4, metalness: 0.3 }));
    cab.position.y = wallH + 0.1; cab.castShadow = true; bridge.add(cab);
    // ذراعا الكشط (ينزلان نحو القاع)
    const armMat = new THREE.MeshStandardMaterial({ color: 0x8fa2b8, roughness: 0.7 });
    [-1, 1].forEach(s => {
      const arm = new THREE.Mesh(new THREE.BoxGeometry(R - 0.4, 0.08, 0.12), armMat);
      arm.position.set(s * (R / 2 - 0.2), 0.2, 0); arm.rotation.z = s * 0.32; bridge.add(arm);
    });
    scene.add(bridge);

    // ---- أنابيب الدخول/الخروج ----
    const pipeMat = new THREE.MeshStandardMaterial({ color: 0x8a705a, roughness: 0.8, metalness: 0.3 });
    [[-1, 0x8a705a], [1, 0x6f8a95]].forEach(([s, col], i) => {
      const pipe = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 3, 20),
        new THREE.MeshStandardMaterial({ color: col, roughness: 0.8, metalness: 0.3 }));
      pipe.rotation.z = Math.PI / 2; pipe.position.set(s * (R + 1.2), 0.1, s * 1.5);
      pipe.castShadow = true; scene.add(pipe);
    });

    // تحكّم دوران بالفأرة (اختياري — نسخة خفيفة يدوية)
    setupDrag();

    if (data) update(data);
    animate();
    global.addEventListener('resize', onResize);
  }

  // دوران يدوي بسيط بالسحب (بدون OrbitControls)
  let dragging = false, px = 0, rotY = 0, userRotY = 0;
  function setupDrag() {
    const el = renderer.domElement;
    el.style.cursor = 'grab';
    el.addEventListener('pointerdown', e => { dragging = true; px = e.clientX; autoRotate = false; el.style.cursor = 'grabbing'; });
    global.addEventListener('pointerup', () => { dragging = false; if (el) el.style.cursor = 'grab'; setTimeout(() => autoRotate = true, 2500); });
    global.addEventListener('pointermove', e => {
      if (!dragging) return;
      userRotY += (e.clientX - px) * 0.008; px = e.clientX;
    });
  }

  function update(d) {
    if (d.blanket != null) {
      // ارتفاع مخروط الحمأة (0.15 .. 0.95 من العمق)
      const frac = Math.max(0.12, Math.min(0.95, d.blanket / (d.swd || 4)));
      blanketTargetY = frac;
      // لون الحمأة حسب الحالة
      const col = d.blanket < 1 ? 0x6b8caf : d.blanket < 3 ? 0x7a5230 : d.blanket < 4 ? 0xa06a2a : 0x8a2b2b;
      if (sludge) sludge.material.color.setHex(col);
    }
    if (d.flow != null) {
      // سرعة دوران الجسر تتناسب مع التدفّق
      targetSpin = 0.003 + (d.flow / 90000) * 0.006;
    }
  }

  function animate() {
    raf = requestAnimationFrame(animate);
    const t = performance.now() * 0.001;
    if (bridge) bridge.rotation.y += targetSpin;
    // تموّج طفيف للماء
    if (waterMat) waterMat.opacity = 0.82 + Math.sin(t * 1.5) * 0.04;
    // انتقال ناعم لارتفاع الحمأة
    if (sludge) sludge.scale.y += (blanketTargetY - sludge.scale.y) * 0.05;
    // دوران المشهد
    if (scene) {
      const base = autoRotate ? (scene.rotation.y + 0.0015) : scene.rotation.y;
      scene.rotation.y = base + (userRotY - (scene._u || 0));
      scene._u = userRotY;
    }
    renderer.render(scene, camera);
  }

  function onResize() {
    if (!container) return;
    W = container.clientWidth; H = container.clientHeight || 420;
    camera.aspect = W / H; camera.updateProjectionMatrix();
    renderer.setSize(W, H);
  }

  global.Clarifier3D = { init, update };
})(window);
