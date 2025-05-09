import Navbar from "../../components/Navbar";
import '../../css/Integrations.css'; // Adjusted path

export default function Integrations() { // Changed component name to Integrations
  return (
    <div className="integrations-container">
      <Navbar />
      <main className="integrations-main">
        {/* Placeholder content for Integrations page */}
        <h1 style={{textAlign: 'center', marginTop: '20px'}}>Integrations Page</h1>
        <p style={{textAlign: 'center'}}>Connect your tools and data sources.</p>
      </main>
    </div>
  );
}
