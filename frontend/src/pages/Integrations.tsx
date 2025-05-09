import Navbar from "../components/Navbar";
import PromptInput from "../components/PromptInput";
import ChartRenderer from "../components/ChartRenderer";

export default function Dashboard() {
  return (
    <div className="h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 p-4">
        <PromptInput />
        <ChartRenderer />
      </main>
    </div>
  );
}
