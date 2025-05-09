import { useEffect, useRef } from "react";
import * as d3 from "d3";
import '../css/ChartRenderer.css'; // Import the CSS file

export default function ChartRenderer() {
  const ref = useRef<SVGSVGElement | null>(null); // Added type for ref

  useEffect(() => {
    if (!ref.current) return; // Ensure ref.current is not null
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove(); // Clear previous chart

    // Simple example bar chart
    const data = [10, 30, 50, 80];
    svg
      .selectAll("rect")
      .data(data)
      .enter()
      .append("rect")
      .attr("x", (_d: number, i: number) => i * 40)
      .attr("y", (d: number) => 100 - d)
      .attr("width", 30)
      .attr("height", (d: number) => d)
      .attr("fill", "steelblue");
  }, []);

  // Added a class for potential styling via ChartRenderer.css
  return <svg ref={ref} width={200} height={100} className="chart-renderer-svg"></svg>;
}
