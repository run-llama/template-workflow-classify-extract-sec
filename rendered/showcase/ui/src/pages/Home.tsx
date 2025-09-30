import { Link } from "react-router-dom";

type Showcase = { key: string; title: string; description: string };

const showcases: Showcase[] = [
  {
    key: "streaming",
    title: "Streaming",
    description: "Stream results as they are generated.",
  },
  {
    key: "stateful-query",
    title: "Query",
    description:
      "Query state from a workflow as it runs. e.g. to reload history, or fetch details on demand from the workflow state.",
  },
  {
    key: "stateful-signal",
    title: "Signal",
    description: "Send events to modify the workflow's state as it runs",
  },
  {
    key: "fan-out",
    title: "Fan-Out",
    description: "Run and observe subtasks in parallel",
  },
  {
    key: "pause-for-input",
    title: "Pause for Input",
    description:
      "A maze game that pauses for player input. Demonstrates human-in-the-loop with state persistence.",
  },
];

export default function Home() {
  return (
    <div className="min-h-dvh aurora-container">
      <div className="relative z-10 mx-auto max-w-5xl px-4 py-10 sm:py-14">
        <header className="mb-8 sm:mb-10">
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
            Showcase
          </h1>
          <p className="mt-2 text-sm sm:text-base text-zinc-500 dark:text-zinc-400 max-w-3xl">
            A gallery of small, workflow‑driven patterns demonstrating
            capabilities that can be achieved with Llama Deploy workflows and
            react hooks.
          </p>
        </header>

        <nav aria-label="Showcases">
          <ul className="grid gap-4 sm:gap-5 md:grid-cols-2">
            {showcases.map((s) => (
              <li key={s.key} className="group">
                <Link
                  to={`/${s.key}`}
                  className="block rounded-xl border border-zinc-200/70 dark:border-zinc-800/70 bg-white/50 dark:bg-zinc-900/40 backdrop-blur p-4 sm:p-5 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-base sm:text-lg font-medium">
                        {s.title}
                      </h2>
                      <p className="mt-1 text-xs sm:text-sm text-zinc-600 dark:text-zinc-400">
                        {s.description}
                      </p>
                    </div>
                    <span
                      className="shrink-0 text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-200 transition-colors"
                      aria-hidden
                    >
                      →
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </div>
  );
}
