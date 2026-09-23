import { useEffect, useRef } from "react";
import type { ScanPoint } from "../lib/api";

// Canvas polar plot: 0 deg up, clockwise. Cyan returns, red closest ring.
export default function PolarPlot({
  points,
  rangeMaxMm,
}: {
  points: ScanPoint[];
  rangeMaxMm: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const size = canvas.width;
    const c = size / 2;
    const span = Math.max(rangeMaxMm, 1000);
    const scale = ((size / 2 - 20) * 1.0) / span;
    ctx.fillStyle = "#09090b";
    ctx.fillRect(0, 0, size, size);
    ctx.strokeStyle = "#27272a";
    ctx.lineWidth = 1;
    for (let ring = 1000; ring < span; ring += 1000) {
      ctx.beginPath();
      ctx.arc(c, c, ring * scale, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = "#71717a";
      ctx.font = "11px sans-serif";
      ctx.fillText(`${ring / 1000} m`, c + 4, c - ring * scale - 4);
    }
    ctx.beginPath();
    ctx.moveTo(10, c);
    ctx.lineTo(size - 10, c);
    ctx.moveTo(c, 10);
    ctx.lineTo(c, size - 10);
    ctx.stroke();
    let closest: ScanPoint | null = null;
    ctx.fillStyle = "#22d3ee";
    for (const p of points) {
      if (!p.is_valid) continue;
      const a = (p.angle_deg * Math.PI) / 180;
      const r = p.distance_mm * scale;
      ctx.fillRect(c + r * Math.sin(a) - 1.5, c - r * Math.cos(a) - 1.5, 3, 3);
      if (!closest || p.distance_mm < closest.distance_mm) closest = p;
    }
    ctx.fillStyle = "#fafafa";
    ctx.beginPath();
    ctx.arc(c, c, 4, 0, Math.PI * 2);
    ctx.fill();
    if (closest) {
      const a = (closest.angle_deg * Math.PI) / 180;
      const r = closest.distance_mm * scale;
      const x = c + r * Math.sin(a);
      const y = c - r * Math.cos(a);
      ctx.strokeStyle = "#f43f5e";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, y, 7, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = "#f43f5e";
      ctx.font = "13px sans-serif";
      ctx.fillText(
        `closest: ${closest.distance_mm.toFixed(0)} mm @ ${closest.angle_deg.toFixed(1)} deg`,
        12,
        size - 12,
      );
    }
  }, [points, rangeMaxMm]);
  return (
    <canvas
      ref={ref}
      width={520}
      height={520}
      className="rounded border border-zinc-800"
      data-testid="polar-plot"
    />
  );
}
