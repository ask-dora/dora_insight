import { useEffect, useRef } from "react";
import * as d3 from "d3";

export default function ChartRenderer() {
  const ref = useRef(null);

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove(); // Clear previous chart

    // Simple example bar chart
    const data = [10, 30, 50, 80];
    svg
      .selectAll("rect")
      .data(data)
      .enter()
      .append("rect")
      .attr("x", (_, i) => i * 40)
      .attr("y", (d) => 100 - d)
      .attr("width", 30)
      .attr("height", (d) => d)
      .attr("fill", "steelblue");
  }, []);

  return <svg ref={ref} width={200} height={100}></svg>;
}
