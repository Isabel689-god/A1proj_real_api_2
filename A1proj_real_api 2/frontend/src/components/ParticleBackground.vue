<template>
  <canvas ref="canvas" class="particle-canvas"></canvas>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

const canvas = ref<HTMLCanvasElement | null>(null);
let animationId: number;

onMounted(() => {
  if (!canvas.value) return;
  const ctx = canvas.value.getContext('2d');
  if (!ctx) return;

  let width = window.innerWidth;
  let height = window.innerHeight;

  const resizeCanvas = () => {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.value!.width = width;
    canvas.value!.height = height;
  };
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  // ✅ 3D 透视参数
  const focalLength = 400; // 焦距，控制透视深度
  const centerX = width / 2;
  const centerY = height / 2;

  class Particle3D {
    x: number; y: number; z: number;
    radius: number; color: string;
    velocityZ: number;

    constructor() {
      // 随机分布在 3D 空间
      this.x = (Math.random() - 0.5) * 2000;
      this.y = (Math.random() - 0.5) * 2000;
      this.z = Math.random() * 2000;
      this.radius = Math.random() * 2 + 1;
      this.velocityZ = -(Math.random() * 2 + 1); // 向屏幕外运动
      this.color = `rgba(107, 137, 196, ${Math.random() * 0.6 + 0.1})`;
    }

    update() {
      this.z += this.velocityZ;
      // 当粒子跑出屏幕范围后，重置到远端
      if (this.z <= 0) {
        this.z = 2000;
        this.x = (Math.random() - 0.5) * 2000;
        this.y = (Math.random() - 0.5) * 2000;
      }
    }

    draw() {
      // 3D 坐标投影到 2D 屏幕
      const scale = focalLength / (focalLength + this.z);
      const screenX = centerX + this.x * scale;
      const screenY = centerY + this.y * scale;
      const screenRadius = this.radius * scale;

      // 如果超出屏幕就不画了
      if (screenX < 0 || screenX > width || screenY < 0 || screenY > height) return;

      ctx!.beginPath();
      ctx!.arc(screenX, screenY, screenRadius, 0, Math.PI * 2);
      ctx!.fillStyle = this.color;
      ctx!.fill();

      return { screenX, screenY, scale }; // 返回坐标供连线使用
    }
  }

  const particles: Particle3D[] = Array.from({ length: 300 }, () => new Particle3D());

  const animate = () => {
    ctx!.clearRect(0, 0, width, height);

    // 获取投影后的2D坐标系
    const projectedNodes = [];

    for (const p of particles) {
      p.update();
      const proj = p.draw();
      if (proj && p.z < 1500) { // 只连接距离适中的点
        projectedNodes.push(proj);
      }
    }

    // 绘制3D网格连线 (增加科技感)
    for (let i = 0; i < projectedNodes.length; i++) {
      for (let j = i + 1; j < projectedNodes.length; j++) {
        const dx = projectedNodes[i].screenX - projectedNodes[j].screenX;
        const dy = projectedNodes[i].screenY - projectedNodes[j].screenY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 100) {
          ctx!.beginPath();
          // 根据距离和Z轴深度计算透明度
          const alpha = 0.3 * (1 - dist / 100) * projectedNodes[i].scale;
          ctx!.strokeStyle = `rgba(107, 137, 196, ${alpha * 0.7})`;
          ctx!.lineWidth = 0.5;
          ctx!.moveTo(projectedNodes[i].screenX, projectedNodes[i].screenY);
          ctx!.lineTo(projectedNodes[j].screenX, projectedNodes[j].screenY);
          ctx!.stroke();
        }
      }
    }

    animationId = requestAnimationFrame(animate);
  };

  animate();

  onUnmounted(() => {
    window.removeEventListener('resize', resizeCanvas);
    cancelAnimationFrame(animationId);
  });
});
</script>

<style scoped>
.particle-canvas {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
  /* 极深海军蓝向外扩散 */
  background: radial-gradient(circle at center, #0a0f1d 0%, #060913 100%);
}
</style>