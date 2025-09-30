import { useEffect, useMemo, useRef, useState } from "react";

type SparklineProps = {
  values: number[];
  height?: number;
  maxVisible?: number;
  strokeWidth?: number;
  animate?: boolean;
  color?: string;
  fixedRange?: [number, number]; // [min, max] for fixed y-axis scale
};

// Simple Catmull-Rom spline for smooth curves
function createSmoothPath(points: Array<{ x: number; y: number }>): string {
  if (points.length === 0) return "";
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
  if (points.length === 2)
    return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;

  let path = `M ${points[0].x} ${points[0].y}`;

  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i === 0 ? i : i - 1];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || p2;

    // Catmull-Rom to Bezier conversion (tension = 0.5 for standard Catmull-Rom)
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;

    path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
  }

  return path;
}

export function Sparkline({
  values,
  height = 50,
  maxVisible = 80,
  strokeWidth = 3,
  animate = true,
  color = "#0891b2",
  fixedRange,
}: SparklineProps) {
  // Take last maxVisible + 2 points for smooth animation (extra for left exit)
  const visibleValues = useMemo(
    () => values.slice(-Math.min(values.length, maxVisible + 2)),
    [values, maxVisible],
  );

  const [minY, maxY] = useMemo((): [number, number] => {
    // Use fixed range if provided
    if (fixedRange) {
      return fixedRange;
    }

    // Otherwise calculate dynamic range from visible values
    if (visibleValues.length === 0) return [0, 1];
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    for (const v of visibleValues) {
      if (v < min) min = v;
      if (v > max) max = v;
    }
    if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1];
    if (min === max) {
      const eps = min === 0 ? 1 : Math.abs(min) * 0.01;
      return [min - eps, max + eps];
    }
    return [min, max];
  }, [visibleValues, fixedRange]);

  // Use a viewBox height that creates a more reasonable aspect ratio
  // This reduces stretching of effects like drop-shadow
  const viewBoxHeight = maxVisible / 8; // Creates roughly 8:1 aspect ratio
  const verticalPadding = viewBoxHeight * 0.15; // 15% padding top/bottom

  const { path, translatePercent } = useMemo(() => {
    if (visibleValues.length === 0) return { path: "", translatePercent: 0 };

    const range = maxY - minY || 1;
    const points: Array<{ x: number; y: number }> = [];
    const totalSegments = values.length - 1;
    const stepPercent = 100 / maxVisible;

    // When overflowing, draw path at its absolute position so it can be cropped by translate
    // When not overflowing, draw at relative position [0..n]
    if (totalSegments >= maxVisible) {
      // Overflowing: draw the last maxVisible+1 points at their absolute positions
      const startSegment = totalSegments - (visibleValues.length - 1);
      for (let i = 0; i < visibleValues.length; i++) {
        const x = startSegment + i;
        const y =
          verticalPadding +
          (1 - (visibleValues[i] - minY) / range) * viewBoxHeight;
        points.push({ x, y });
      }
      // Translate to show segments [totalSegments - maxVisible .. totalSegments]
      const overflow = totalSegments - maxVisible;
      const translatePercent = -overflow * stepPercent;
      return { path: createSmoothPath(points), translatePercent };
    } else {
      // Not full yet: draw at relative positions and right-align
      for (let i = 0; i < visibleValues.length; i++) {
        const x = i;
        const y =
          verticalPadding +
          (1 - (visibleValues[i] - minY) / range) * viewBoxHeight;
        points.push({ x, y });
      }
      const emptySpace = maxVisible - totalSegments;
      const translatePercent = emptySpace * stepPercent;
      return { path: createSmoothPath(points), translatePercent };
    }
  }, [
    visibleValues,
    minY,
    maxY,
    values.length,
    maxVisible,
    viewBoxHeight,
    verticalPadding,
  ]);

  const [delayComplete, setDelayComplete] = useState(false);
  useEffect(() => {
    setTimeout(() => setDelayComplete(true), 150);
  }, []);
  const reallyAnimate = animate && delayComplete;

  return (
    <div
      className="w-full border-1 border-zinc-200/70 dark:border-zinc-800/70 rounded-md overflow-hidden"
      style={{ height }}
    >
      <div
        className={`w-full h-full ${reallyAnimate ? "transition-transform duration-500 ease-linear" : ""}`}
        style={{
          transform: `translateX(${translatePercent}%)`,
          willChange: "transform",
        }}
      >
        <svg
          className="w-full h-full overflow-visible"
          viewBox={`0 0 ${maxVisible} ${viewBoxHeight + verticalPadding * 2}`}
          preserveAspectRatio="none"
        >
          {path && (
            <path
              d={path}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
              style={{
                filter: `drop-shadow(0 0 0.0125px ${color}) drop-shadow(0 0 0.025px ${color})`,
              }}
            />
          )}
        </svg>
      </div>
    </div>
  );
}
