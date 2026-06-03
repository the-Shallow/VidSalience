import { Link } from "react-router-dom";
import { ArrowRight, Eye, Gauge, Layers } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { Button } from "@/components/ui/button";
import { PipelineDiagram } from "@/components/PipelineDiagram";

// export const Route = createFileRoute("/")({
//   head: () => ({
//     meta: [
//       { title: "VidSalience — AI-powered saliency-aware video compression" },
//       { name: "description", content: "Preserve what the eye sees. VidSalience uses saliency detection to compress video intelligently while keeping perceptually important regions sharp." },
//       { property: "og:title", content: "VidSalience" },
//       { property: "og:description", content: "AI-powered saliency-aware video compression." },
//     ],
//   }),
//   component: Index,
// });

function Index() {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main>
        {/* Hero */}
        <section
          className="relative overflow-hidden"
          style={{ backgroundImage: "var(--gradient-subtle)" }}
        >
          <div
            aria-hidden
            className="pointer-events-none absolute -top-32 left-1/2 h-[480px] w-[900px] -translate-x-1/2 rounded-full opacity-30 blur-3xl"
            style={{ backgroundImage: "var(--gradient-primary)" }}
          />
          <div className="relative mx-auto max-w-5xl px-6 py-24 text-center sm:py-32">
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              Research preview · v0.1
            </span>
            <h1 className="mt-6 text-5xl font-semibold tracking-tight sm:text-7xl">
              Vid<span className="bg-clip-text text-transparent" style={{ backgroundImage: "var(--gradient-primary)" }}>Salience</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground sm:text-xl">
              AI-powered saliency-aware video compression.
            </p>
            <p className="mx-auto mt-4 max-w-2xl text-base text-muted-foreground/90">
              VidSalience uses neural saliency models to detect where the human eye looks. Important regions stay sharp; everything else is compressed aggressively — shrinking file size without sacrificing perceived quality.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <Button asChild size="lg" className="shadow-[var(--shadow-elegant)]">
                <Link to="/upload">
                  Upload Video <ArrowRight className="ml-1.5 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <a href="#how">How it works</a>
              </Button>
            </div>
            <div className="mx-auto mt-12 max-w-3xl text-left">
              <PipelineDiagram />
            </div>
          </div>
        </section>

        {/* Features */}
        <section id="how" className="mx-auto max-w-6xl px-6 py-20">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">A new way to compress video</h2>
            <p className="mt-4 text-muted-foreground">
              Three stages, one pipeline — built for researchers and product teams who care about perceptual quality.
            </p>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            <FeatureCard
              icon={<Eye className="h-5 w-5" />}
              title="Saliency Detection"
              description="A deep model predicts per-frame attention maps, identifying regions a viewer is most likely to look at."
            />
            <FeatureCard
              icon={<Layers className="h-5 w-5" />}
              title="Attention-Aware Compression"
              description="The encoder allocates more bits to salient regions and aggressively compresses the rest — shrinking files without visible loss."
            />
            <FeatureCard
              icon={<Gauge className="h-5 w-5" />}
              title="Quality Metrics"
              description="Every job ships with PSNR, SSIM, and a saliency-weighted PSNR so you can measure what actually matters."
            />
          </div>
        </section>
      </main>
      <footer className="border-t border-border/60 py-8 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} VidSalience · Research project
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div
      className="group relative rounded-2xl border border-border bg-card p-6 transition-all hover:-translate-y-0.5"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div
        className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg text-primary-foreground"
        style={{ backgroundImage: "var(--gradient-primary)" }}
      >
        {icon}
      </div>
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
    </div>
  );
}


export default Index;