import Nav from "./sections/Nav";
import Hero from "./sections/Hero";
import Features from "./sections/Features";
import Science from "./sections/Science";
import Pricing from "./sections/Pricing";
import Footer from "./sections/Footer";

/** Where the "Open app" CTAs point (the separate frontend). */
export const APP_URL = import.meta.env.VITE_APP_URL || "http://localhost:5173";

export default function App() {
  return (
    <div className="shell">
      <Nav appUrl={APP_URL} />
      <main>
        <Hero appUrl={APP_URL} />
        <Features />
        <Science />
        <Pricing appUrl={APP_URL} />
      </main>
      <Footer appUrl={APP_URL} />
    </div>
  );
}
