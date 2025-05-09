import Navbar from "../../components/Navbar";
import PromptInput from "../../components/PromptInput";
import ChartRenderer from "../../components/ChartRenderer";
import '../../css/Dashboard.css'; // Adjusted path

export default function Dashboard() {
  return (
    <div className="dashboard-container">
      <Navbar />
      <main className="dashboard-main">
        <PromptInput />
        <ChartRenderer />
      </main>
    </div>
  );
}
