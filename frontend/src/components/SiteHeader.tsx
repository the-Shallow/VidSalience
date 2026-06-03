import { NavLink } from "react-router-dom";
import { Sparkles } from "lucide-react";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/60 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <NavLink to="/" className="flex items-center gap-2 group">
          <span
            className="flex h-9 w-9 items-center justify-center rounded-lg text-primary-foreground shadow-md transition-transform group-hover:scale-105"
            style={{ backgroundImage: "var(--gradient-primary)" }}
          >
            <Sparkles className="h-4 w-4" />
          </span>
          <div className="flex flex-col leading-tight">
            <span className="text-sm font-semibold tracking-tight">VidSalience</span>
            <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Research Preview
            </span>
          </div>
        </NavLink>

        <nav className="flex items-center gap-1 text-sm">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              isActive
                ? "rounded-md px-3 py-2 text-foreground bg-accent"
                : "rounded-md px-3 py-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            }
          >
            Home
          </NavLink>

          <NavLink
            to="/upload"
            className={({ isActive }) =>
              isActive
                ? "rounded-md px-3 py-2 text-foreground bg-accent"
                : "rounded-md px-3 py-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            }
          >
            Upload
          </NavLink>
        </nav>
      </div>
    </header>
  );
}